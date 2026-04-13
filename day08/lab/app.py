"""
app.py — RAG Question Testing UI
=================================
Streamlit UI với 3 cột:
  Left  : Nhập câu hỏi
  Middle: LLM đọc intent và sinh VARIANT_CONFIG tối ưu
  Right : Câu trả lời, sources, chunks retrieved

Chạy:
    streamlit run app.py
"""

import json
import os
import sys

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# Thêm thư mục lab vào sys.path để import rag_answer
sys.path.insert(0, os.path.dirname(__file__))
from rag_answer import rag_answer  # noqa: E402

# =============================================================================
# CẤU HÌNH TRANG
# =============================================================================

st.set_page_config(
    page_title="RAG Question Tester",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 RAG Question Testing UI")
st.caption("LLM tự động phân tích intent câu hỏi và chọn cấu hình retrieval tối ưu.")

# =============================================================================
# LLM INTENT ANALYZER
# =============================================================================

INTENT_SYSTEM_PROMPT = """Bạn là chuyên gia tối ưu hệ thống RAG. Nhiệm vụ: phân tích intent của câu hỏi và sinh ra cấu hình retrieval phù hợp nhất.

Corpus nội bộ gồm: chính sách hoàn tiền, SLA ticket, quy trình cấp quyền hệ thống, IT helpdesk FAQ, HR leave policy.

Quy tắc chọn config:
- natural_language (câu hỏi ngôn ngữ tự nhiên, không có keyword đặc biệt):
    retrieval_mode=dense, dense_weight=0.7, sparse_weight=0.3
- keyword_heavy (có mã lỗi, tên viết tắt, mức SLA như P1/P2, level quyền):
    retrieval_mode=hybrid, dense_weight=0.4, sparse_weight=0.6, use_rerank=true
- alias_query (dùng tên cũ, biệt danh, từ đồng nghĩa — ví dụ: "Approval Matrix"):
    retrieval_mode=hybrid, dense_weight=0.5, sparse_weight=0.5, use_query_transform=true, transform_strategy=expansion
- multi_part (hỏi nhiều thứ cùng lúc):
    retrieval_mode=hybrid, use_query_transform=true, transform_strategy=decomposition
- insufficient_context (câu hỏi về thông tin không có trong corpus — lỗi không rõ, quy trình VIP, ngoại lệ):
    retrieval_mode=dense, use_rerank=false (pipeline sẽ tự abstain)

Trả về JSON hợp lệ với đúng các field sau (không có field nào khác):
{
  "intent_type": "<natural_language|keyword_heavy|alias_query|multi_part|insufficient_context>",
  "intent_summary": "<một câu mô tả ngắn gọn intent>",
  "reasoning": "<giải thích tại sao chọn config này>",
  "config": {
    "retrieval_mode": "<dense|sparse|hybrid>",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": <true|false>,
    "use_query_transform": <true|false>,
    "transform_strategy": "<expansion|decomposition|hyde>",
    "dense_weight": <0.0-1.0>,
    "sparse_weight": <0.0-1.0>
  }
}"""


@st.cache_data(show_spinner=False)
def analyze_intent(query: str) -> dict:
    """Gọi LLM để phân tích intent và sinh config."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": f'Câu hỏi: "{query}"'},
        ],
        temperature=0,
        max_tokens=512,
        response_format={"type": "json_object"},
    )
    return json.loads(response.choices[0].message.content)


# =============================================================================
# UI LAYOUT
# =============================================================================

col_left, col_mid, col_right = st.columns([1.2, 1.4, 1.8], gap="large")

# ---------- LEFT: Input ----------
with col_left:
    st.subheader("Câu hỏi")
    query = st.text_area(
        label="Nhập câu hỏi:",
        placeholder="VD: SLA xử lý ticket P1 là bao lâu?",
        height=120,
        label_visibility="collapsed",
    )

    manual_override = st.toggle("Tùy chỉnh config thủ công", value=False)

    if manual_override:
        st.markdown("**Override config:**")
        retrieval_mode = st.selectbox("retrieval_mode", ["dense", "hybrid", "sparse"], index=1)
        use_rerank = st.checkbox("use_rerank", value=True)
        use_query_transform = st.checkbox("use_query_transform", value=False)
        transform_strategy = st.selectbox("transform_strategy", ["expansion", "decomposition", "hyde"])
        dense_weight = st.slider("dense_weight", 0.0, 1.0, 0.6, 0.05)
        sparse_weight = round(1.0 - dense_weight, 2)
        st.caption(f"sparse_weight = {sparse_weight} (tự động)")

    submitted = st.button("🚀 Gửi câu hỏi", use_container_width=True, type="primary")

# ---------- MIDDLE: Intent + Config ----------
with col_mid:
    st.subheader("Intent & Config")

    if submitted and query.strip():
        with st.spinner("LLM đang phân tích intent..."):
            try:
                analysis = analyze_intent(query.strip())
            except Exception as e:
                st.error(f"Lỗi phân tích intent: {e}")
                analysis = None

        if analysis:
            intent_type = analysis.get("intent_type", "unknown")
            intent_colors = {
                "natural_language": "🟢",
                "keyword_heavy": "🟡",
                "alias_query": "🟠",
                "multi_part": "🔵",
                "insufficient_context": "🔴",
            }
            icon = intent_colors.get(intent_type, "⚪")

            st.markdown(f"**Intent:** {icon} `{intent_type}`")
            st.markdown(f"**Tóm tắt:** {analysis.get('intent_summary', '')}")
            st.markdown(f"**Lý do:** {analysis.get('reasoning', '')}")

            generated_config = analysis.get("config", {})

            st.divider()
            st.markdown("**Config được sinh ra:**")
            st.json(generated_config, expanded=True)

            # Lưu config vào session để dùng ở cột phải
            st.session_state["generated_config"] = generated_config
            st.session_state["analysis"] = analysis

    elif submitted and not query.strip():
        st.warning("Vui lòng nhập câu hỏi.")

    if not submitted:
        st.info("Nhập câu hỏi và nhấn **Gửi câu hỏi** để bắt đầu.")

# ---------- RIGHT: Answer ----------
with col_right:
    st.subheader("Câu trả lời")

    if submitted and query.strip() and (
        "generated_config" in st.session_state or manual_override
    ):
        # Xác định config sẽ dùng
        if manual_override:
            final_config = {
                "retrieval_mode": retrieval_mode,
                "top_k_search": 10,
                "top_k_select": 3,
                "use_rerank": use_rerank,
                "use_query_transform": use_query_transform,
                "transform_strategy": transform_strategy,
                "dense_weight": dense_weight,
                "sparse_weight": sparse_weight,
            }
        else:
            final_config = st.session_state.get("generated_config", {})

        with st.spinner("Đang retrieve và generate câu trả lời..."):
            try:
                result = rag_answer(
                    query=query.strip(),
                    retrieval_mode=final_config.get("retrieval_mode", "dense"),
                    top_k_search=final_config.get("top_k_search", 10),
                    top_k_select=final_config.get("top_k_select", 3),
                    use_rerank=final_config.get("use_rerank", False),
                    use_query_transform=final_config.get("use_query_transform", False),
                    transform_strategy=final_config.get("transform_strategy", "expansion"),
                    dense_weight=final_config.get("dense_weight", 0.6),
                    sparse_weight=final_config.get("sparse_weight", 0.4),
                    verbose=False,
                )
                error = None
            except Exception as e:
                result = None
                error = str(e)

        if error:
            st.error(f"Lỗi pipeline: {error}")
        elif result:
            answer = result["answer"]

            # Highlight abstain
            if answer == "Không đủ dữ liệu":
                st.warning(f"⚠️ **Abstain:** {answer}")
            else:
                st.success(answer)

            st.divider()

            # Sources
            sources = result.get("sources", [])
            if sources:
                st.markdown("**Nguồn trích dẫn:**")
                for src in sources:
                    st.markdown(f"- `{src}`")

            # Chunks
            chunks = result.get("chunks_used", [])
            if chunks:
                st.markdown(f"**Chunks retrieved ({len(chunks)}):**")
                for i, chunk in enumerate(chunks, 1):
                    meta = chunk.get("metadata", {})
                    score = chunk.get("score", 0)
                    source = meta.get("source", "unknown")
                    section = meta.get("section", "")
                    text = chunk.get("text", "")[:300]

                    label = f"[{i}] {source}"
                    if section:
                        label += f" | {section}"
                    if score:
                        label += f" | score={score:.3f}"

                    with st.expander(label):
                        st.text(text + ("..." if len(chunk.get("text", "")) > 300 else ""))

    elif not submitted:
        st.info("Kết quả sẽ hiển thị ở đây sau khi gửi câu hỏi.")
