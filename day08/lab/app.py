"""
Streamlit demo — CS/IT RAG assistant (Day 08 lab).
Chạy: streamlit run app.py  (từ thư mục lab, đã có .env và chroma_db)
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from eval import (
    BASELINE_CONFIG,
    VARIANT_CONFIG,
    TEST_QUESTIONS_PATH,
    USE_LLM_JUDGE,
    ab_comparison_rows,
    average_metric_scores,
    compare_ab,
    generate_scorecard_summary,
    run_scorecard,
)

from rag_answer import rag_answer

LAB = Path(__file__).parent
RESULTS_DIR = LAB / "results"


@st.cache_data
def load_test_questions():
    if not TEST_QUESTIONS_PATH.exists():
        return []
    with open(TEST_QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# --- Theo slide Ngày 8 (mục 4.1 RAG Evaluation Triad + lab) ---
SCORECARD_TRIAD_MD = """
**Tam giác đánh giá RAG (RAGAS)** — slide *4.1 The RAG Evaluation Triad*: không gom một con số;
tách lỗi **retrieval** vs **generation**.

| Chỉ số | Đo cái gì? | Gợi ý khi thấp |
|--------|------------|----------------|
| **Context recall** | Retriever có lôi đủ **chứng cứ** cần cho câu hỏi không? | Hybrid search, tăng top-k, chunking |
| **Faithfulness** | Câu trả lời có **bám sát context** hay bịa thêm? | Prompt grounding, trích dẫn, temperature = 0 |
| **Answer relevance** | Có **đúng trọng tâm** câu hỏi không (không lan man)? | Rerank, lọc context nhiễu |

**Completeness** (thêm trong lab): so với **đáp án mẫu** `expected_answer` trong `test_questions.json`.

Chấm tự động: **LLM-as-a-Judge** (slide 4.1). Đặt `USE_LLM_JUDGE=0` trong `.env` nếu chỉ muốn recall (không gọi judge).
"""


def render_pipeline_steps(steps: List[Dict[str, Any]]) -> None:
    """Timeline các bước RAG (rag_answer trace)."""
    st.markdown("#### Các bước hệ thống vừa chạy")
    st.caption(
        "Giống pipeline trên slide: query → retrieve rộng → (rerank) → chọn top-k → "
        "ghép context + prompt grounded → LLM."
    )
    for s in steps:
        emoji = s.get("emoji", "•")
        title = s.get("name", "")
        num = s.get("step", "")
        with st.container(border=True):
            st.markdown(f"**{emoji} Bước {num}: {title}**")
            if s.get("detail"):
                st.markdown(s["detail"])
            if s.get("query") is not None:
                st.info(s["query"])
            if s.get("table"):
                st.caption("Ứng viên (preview)")
                st.dataframe(s["table"], use_container_width=True, hide_index=True)
            if s.get("context_preview"):
                with st.expander("Preview context gửi vào LLM", expanded=False):
                    st.text(s["context_preview"])
            if s.get("prompt_preview"):
                with st.expander("Preview prompt đầy đủ", expanded=False):
                    st.text(s["prompt_preview"])
            if title == "LLM" and s.get("answer_chars") is not None:
                st.success(
                    f"Đã gọi LLM (**{s['answer_chars']}** ký tự). Kết quả hiển thị ở mục **Câu trả lời** bên dưới."
                )


def _metric_bar(label: str, value: float | None, help_text: str = "") -> None:
    if value is None:
        st.metric(label, "N/A", help=help_text)
    else:
        st.metric(label, f"{value:.2f} / 5", help=help_text)


def main() -> None:
    st.set_page_config(
        page_title="Day 08 — RAG Lab",
        page_icon="📋",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("Trợ lý chính sách CS / IT (RAG)")
    st.markdown(
        "Lab **Day 08**: *index → retrieve → (rerank) → sinh câu trả lời có trích dẫn*. "
        "Dùng tab **Scorecard** để đo chất lượng theo slide (không chỉ “vibe check”)."
    )

    with st.expander("Bắt đầu nhanh — đọc nếu bạn mới mở app lần đầu", expanded=False):
        st.markdown(
            """
1. **Hỏi đáp** — chọn câu mẫu hoặc tự gõ → **Chạy RAG** → đọc câu trả lời và khối **Nguồn tham khảo** (slide UX: dễ quét mắt).
2. **Scorecard** — chạy toàn bộ `data/test_questions.json` → xem 4 chỉ số; so **baseline** (dense) vs **variant** (hybrid + rerank).
3. **So sánh A/B** — bảng từng câu: ai thắng baseline hay variant. Slide nhắc: khi **tự tune**, mỗi lần chỉ đổi **một** biến (chunk / hybrid / rerank / prompt) để biết việc gì có tác dụng.

**Cần:** file `.env` có `OPENAI_API_KEY`, đã chạy `python index.py build`, và `EMBEDDING_PROVIDER` khớp lúc build.
            """
        )

    # --- Sidebar ---
    with st.sidebar:
        st.header("Cấu hình pipeline")
        preset = st.radio(
            "Chế độ",
            ["Khuyến nghị lab (giống variant trong code)", "Tùy chỉnh tay"],
            index=0,
            help="Variant = hybrid + rerank + top_k theo eval.VARIANT_CONFIG — thường dùng để nộp bài / demo.",
        )

        if preset.startswith("Khuyến nghị"):
            mode = VARIANT_CONFIG["retrieval_mode"]
            use_rerank = bool(VARIANT_CONFIG["use_rerank"])
            top_k_search = int(VARIANT_CONFIG["top_k_search"])
            top_k_select = int(VARIANT_CONFIG["top_k_select"])
            st.caption(
                f"Đang dùng: **{mode}**, rerank={'bật' if use_rerank else 'tắt'}, "
                f"search={top_k_search}, vào prompt={top_k_select}"
            )
        else:
            mode = st.selectbox(
                "Kiểu retrieval",
                ["dense", "sparse", "hybrid"],
                index=2,
                help="Dense: vector. Sparse: BM25. Hybrid: RRF gộp hai tuyến (slide module 2).",
            )
            use_rerank = st.checkbox(
                "Bật rerank (cross-encoder)",
                value=True,
                help="Slide: search rộng rồi chấm lại từng cặp (query, chunk) — chính xác hơn bi-encoder thuần.",
            )
            top_k_search = st.slider(
                "Số chunk sau bước retrieve (pool)",
                5,
                30,
                int(VARIANT_CONFIG["top_k_search"]),
                help="Slide: không phải càng nhiều càng tốt; sweet spot thường 3–5 vào LLM sau rerank.",
            )
            top_k_select = st.slider(
                "Số chunk đưa vào prompt",
                1,
                8,
                int(VARIANT_CONFIG["top_k_select"]),
            )

        show_steps = st.checkbox(
            "Hiện từng bước pipeline (trace)",
            value=True,
            help="Tương tự hiển thị ‘đang tìm / đang đọc’ — giảm cảm giác app bị treo (slide UX).",
        )

        st.divider()
        st.caption("Judge scorecard")
        st.caption(
            "USE_LLM_JUDGE="
            f"**{1 if USE_LLM_JUDGE else 0}** "
            + ("(faithfulness, relevance, completeness có điểm)" if USE_LLM_JUDGE else "(chỉ recall / số khác có thể N/A)")
        )

    tab_ask, tab_score, tab_ab = st.tabs(
        ["Hỏi đáp", "Scorecard & metrics", "So sánh A/B"]
    )

    # ----- Tab 1 -----
    with tab_ask:
        st.subheader("Thử một câu hỏi")
        qs = load_test_questions()
        preset_labels = [""] + [
            f"{q['id']}: {(q['question'][:56] + '…') if len(q['question']) > 56 else q['question']}"
            for q in qs
        ]
        preset = st.selectbox("Câu mẫu (hoặc để trống)", preset_labels)
        default_q = ""
        if preset and qs:
            idx = preset_labels.index(preset) - 1
            if idx >= 0:
                default_q = qs[idx]["question"]

        query = st.text_area("Nội dung câu hỏi", value=default_q, height=110, placeholder="VD: SLA xử lý ticket P1 là bao lâu?")
        run = st.button("Chạy RAG", type="primary")
        if run and query.strip():
            with st.status("Đang retrieve và gọi LLM…", expanded=True) as status:
                st.write("Bước 1: embedding + tìm chunk trong Chroma")
                st.write("Bước 2: chọn chunk (rerank hoặc cắt top-k)")
                st.write("Bước 3: sinh câu trả lời grounded")
                result = rag_answer(
                    query.strip(),
                    retrieval_mode=mode,
                    top_k_search=top_k_search,
                    top_k_select=top_k_select,
                    use_rerank=use_rerank,
                    verbose=False,
                    trace=show_steps,
                )
                status.update(label="Xong", state="complete")

            if show_steps and result.get("pipeline_steps"):
                render_pipeline_steps(result["pipeline_steps"])
                st.divider()

            st.markdown("##### Câu trả lời")
            st.write(result.get("answer") or "—")

            st.markdown("##### Nguồn tham khảo")
            srcs = result.get("sources") or []
            if srcs:
                for i, s in enumerate(srcs, 1):
                    st.markdown(f"{i}. `{s}`")
            else:
                st.caption("Không có — có thể không retrieve được chunk hoặc lỗi pipeline.")

            tel = result.get("telemetry")
            if tel:
                st.info(
                    f"**Telemetry (slide ROI):** ~**${tel['cost_usd']['total_usd']:.4f}** · "
                    f"**{tel['duration_ms']:.0f} ms** · đã append `logs/runs.jsonl` "
                    f"(run_id `{tel['run_id'][:8]}…`)"
                )

            with st.expander("Chi tiết chunk đã đưa vào prompt", expanded=False):
                for i, ch in enumerate(result.get("chunks_used") or [], 1):
                    meta = ch.get("metadata") or {}
                    st.markdown(f"**[{i}]** `{meta.get('source', '')}` · *{meta.get('section', '')}*")
                    st.text((ch.get("text") or "")[:1200])
        elif run:
            st.warning("Vui lòng nhập câu hỏi.")

    # ----- Tab 2 -----
    with tab_score:
        st.subheader("Scorecard trên `test_questions.json`")
        with st.expander("Scorecard đo gì? (theo slide Ngày 8)", expanded=True):
            st.markdown(SCORECARD_TRIAD_MD)

        nq = len(load_test_questions())
        st.markdown(
            f"Chạy **{nq}** câu trong `data/test_questions.json` — **hai lần**: "
            f"baseline `{BASELINE_CONFIG['label']}` vs variant `{VARIANT_CONFIG['label']}`."
        )
        if not USE_LLM_JUDGE:
            st.warning(
                "Đang tắt LLM judge (`USE_LLM_JUDGE=0`). Faithfulness / relevance / completeness có thể là **N/A**."
            )

        if st.button("Chạy scorecard (baseline + variant)", type="primary"):
            tq = load_test_questions()
            if not tq:
                st.error("Không đọc được `test_questions.json`.")
            else:
                with st.spinner("Đang chạy pipeline + chấm điểm — có thể vài phút…"):
                    b = run_scorecard(BASELINE_CONFIG, test_questions=tq, verbose=False)
                    v = run_scorecard(VARIANT_CONFIG, test_questions=tq, verbose=False)

                b_avg = average_metric_scores(b)
                v_avg = average_metric_scores(v)

                st.markdown("#### Trung bình (thang ~1–5)")
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Baseline — {BASELINE_CONFIG['label']}**")
                    _metric_bar("Faithfulness", b_avg.get("faithfulness"), "Bám context?")
                    _metric_bar("Answer relevance", b_avg.get("relevance"), "Đúng trọng tâm?")
                    _metric_bar("Context recall", b_avg.get("context_recall"), "Đủ expected sources?")
                    _metric_bar("Completeness", b_avg.get("completeness"), "So với đáp án mẫu")
                with c2:
                    st.markdown(f"**Variant — {VARIANT_CONFIG['label']}**")
                    _metric_bar("Faithfulness", v_avg.get("faithfulness"), "Bám context?")
                    _metric_bar("Answer relevance", v_avg.get("relevance"), "Đúng trọng tâm?")
                    _metric_bar("Context recall", v_avg.get("context_recall"), "Đủ expected sources?")
                    _metric_bar("Completeness", v_avg.get("completeness"), "So với đáp án mẫu")

                st.markdown("#### Bảng từng câu (variant)")
                df_v = pd.DataFrame(
                    [
                        {
                            "ID": r["id"],
                            "Faith.": r.get("faithfulness"),
                            "Rel.": r.get("relevance"),
                            "Recall": r.get("context_recall"),
                            "Comp.": r.get("completeness"),
                            "Ghi chú": (r.get("faithfulness_notes") or "")[:60],
                        }
                        for r in v
                    ]
                )
                st.dataframe(df_v, use_container_width=True, hide_index=True)

                RESULTS_DIR.mkdir(parents=True, exist_ok=True)
                (RESULTS_DIR / "scorecard_baseline.md").write_text(
                    generate_scorecard_summary(b, "baseline_dense"), encoding="utf-8"
                )
                (RESULTS_DIR / "scorecard_variant.md").write_text(
                    generate_scorecard_summary(v, VARIANT_CONFIG["label"]),
                    encoding="utf-8",
                )
                st.success(
                    f"Đã ghi `{RESULTS_DIR / 'scorecard_baseline.md'}` và "
                    f"`{RESULTS_DIR / 'scorecard_variant.md'}`."
                )

                with st.expander("Markdown đầy đủ (copy cho báo cáo)"):
                    st.markdown(generate_scorecard_summary(b, "baseline_dense"))
                    st.markdown("---")
                    st.markdown(generate_scorecard_summary(v, VARIANT_CONFIG["label"]))

    # ----- Tab 3 -----
    with tab_ab:
        st.subheader("A/B: baseline vs variant")
        st.markdown(
            "Slide **4.2**: chỉ đổi **một** biến mỗi lần tune; scorecard để stakeholder thấy trước/sau. "
            "Ở đây baseline = **dense**, variant = **hybrid + rerank** (cấu hình trong `eval.py`)."
        )
        if st.button("Chạy so sánh A/B"):
            tq = load_test_questions()
            if not tq:
                st.error("Không có test_questions.json")
            else:
                with st.spinner("Đang chạy A/B…"):
                    b = run_scorecard(BASELINE_CONFIG, test_questions=tq, verbose=False)
                    v = run_scorecard(VARIANT_CONFIG, test_questions=tq, verbose=False)

                b_avg = average_metric_scores(b)
                v_avg = average_metric_scores(v)
                delta_rows = []
                for m in ["faithfulness", "relevance", "context_recall", "completeness"]:
                    bv, vv = b_avg.get(m), v_avg.get(m)
                    d = (vv - bv) if (bv is not None and vv is not None) else None
                    delta_rows.append(
                        {
                            "Metric": m.replace("_", " ").title(),
                            "Baseline": f"{bv:.2f}" if bv is not None else "N/A",
                            "Variant": f"{vv:.2f}" if vv is not None else "N/A",
                            "Δ": f"{d:+.2f}" if d is not None else "N/A",
                        }
                    )
                st.markdown("#### Tổng hợp trung bình")
                st.dataframe(pd.DataFrame(delta_rows), use_container_width=True, hide_index=True)

                st.markdown("#### Theo từng câu hỏi")
                ab_df = pd.DataFrame(ab_comparison_rows(b, v))
                st.dataframe(ab_df, use_container_width=True, hide_index=True)

                with st.expander("Bản in text (giống console `compare_ab`)"):
                    import io
                    import sys

                    buf = io.StringIO()
                    old = sys.stdout
                    sys.stdout = buf
                    try:
                        compare_ab(b, v)
                    finally:
                        sys.stdout = old
                    st.code(buf.getvalue(), language="text")


if __name__ == "__main__":
    main()
