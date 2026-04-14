"""
app.py — Gradio UI for Day 09 Supervisor-Worker Graph

Cho phép:
- Chọn câu query mẫu từ dropdown
- Nhập query tùy ý
- Chạy graph và hiển thị kết quả đầy đủ (route, reason, workers, confidence, latency, history, final_answer)
"""

import json
import time

import gradio as gr

from graph import run_graph, save_trace

# ── Câu query mẫu (giống phần __main__ trong graph.py) ──────────────────────
SAMPLE_QUERIES = [
    "SLA xử lý ticket P1 là bao lâu?",
    "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
    "Cần cấp quyền Level 3 để khắc phục P1 khẩn cấp. Quy trình là gì?",
    "Hoàn tiền trong bao nhiêu ngày?",
    "Cần cấp quyền admin access cho contractor?",
    "ERR-5023 xuất hiện lúc 2am — hệ thống khẩn cấp?",
]


# ── Core runner ──────────────────────────────────────────────────────────────
def run_query(query: str, save_trace_flag: bool):
    query = query.strip()
    if not query:
        return (
            "⚠️ Vui lòng nhập hoặc chọn câu query.",
            "", "", "", "", "", "", "",
        )

    result = run_graph(query)

    # ── Basic fields
    route       = result.get("supervisor_route", "—")
    reason      = result.get("route_reason", "—")
    workers     = ", ".join(result.get("workers_called", [])) or "—"
    confidence  = f"{result.get('confidence', 0.0):.2f}"
    latency     = f"{result.get('latency_ms', 0)} ms"
    final_ans   = result.get("final_answer", "").strip() or "*(không có final answer)*"
    sources_raw = result.get("sources", [])
    sources     = "\n".join(f"• {s}" for s in sources_raw) if sources_raw else "*(không có sources)*"
    history_txt = "\n".join(result.get("history", [])) or "*(trống)*"

    # ── Supervisor audit line from route_reason
    mcp_used = "✅ Có" if "mcp_used=True" in reason else "❌ Không"

    # ── Policy result (nếu có)
    policy = result.get("policy_result", {})
    policy_txt = json.dumps(policy, ensure_ascii=False, indent=2) if policy else "*(không có)*"

    # ── Save trace
    trace_path = ""
    if save_trace_flag:
        try:
            trace_path = save_trace(result)
        except Exception as e:
            trace_path = f"[Lỗi lưu trace: {e}]"

    # ── Summary card (markdown)
    summary = f"""
### 📋 Kết quả chạy graph

| Trường | Giá trị |
|---|---|
| **Route** | `{route}` |
| **Workers đã gọi** | `{workers}` |
| **Confidence** | `{confidence}` |
| **Latency** | `{latency}` |
| **MCP được dùng** | {mcp_used} |
| **Risk High** | {"🔴 Có" if result.get("risk_high") else "🟢 Không"} |
| **HITL Triggered** | {"🔴 Có" if result.get("hitl_triggered") else "🟢 Không"} |
{"| **Trace saved** | `" + trace_path + "` |" if trace_path else ""}
"""

    return summary, reason, final_ans, sources, policy_txt, history_txt, route, workers


def fill_from_sample(sample: str):
    """Điền câu query mẫu vào textbox."""
    return sample


# ── Gradio UI ────────────────────────────────────────────────────────────────
with gr.Blocks(
    title="Day 09 — Supervisor-Worker Graph Tester",
    theme=gr.themes.Base(
        primary_hue="indigo",
        secondary_hue="slate",
        font=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
    ),
    css="""
        .result-box textarea { font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem; }
        #run-btn { font-weight: 700; letter-spacing: 0.03em; }
        .label-header { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.6; }
    """,
) as demo:

    gr.Markdown(
        """
# 🤖 Day 09 — Supervisor-Worker Orchestrator
**LangGraph · Supervisor → Worker → Synthesis → Audit**

Nhập query hoặc chọn từ danh sách mẫu, sau đó nhấn **▶ Chạy Graph**.
        """
    )

    with gr.Row():
        with gr.Column(scale=2):
            query_input = gr.Textbox(
                label="📝 Query",
                placeholder="Nhập câu hỏi hoặc chọn mẫu bên dưới…",
                lines=3,
            )
            sample_dropdown = gr.Dropdown(
                choices=SAMPLE_QUERIES,
                label="💡 Câu query mẫu",
                value=None,
                interactive=True,
            )
            with gr.Row():
                run_btn = gr.Button("▶ Chạy Graph", variant="primary", elem_id="run-btn")
                save_cb = gr.Checkbox(label="💾 Lưu trace JSON", value=False)

        with gr.Column(scale=3):
            summary_out = gr.Markdown(value="*Chưa có kết quả — hãy chạy một query.*")

    gr.Markdown("---")

    with gr.Tabs():
        with gr.Tab("📌 Route Reason"):
            reason_out = gr.Textbox(
                label="Route Reason (từ Supervisor)",
                lines=4,
                interactive=False,
                elem_classes=["result-box"],
            )

        with gr.Tab("💬 Final Answer"):
            answer_out = gr.Textbox(
                label="Final Answer (từ Synthesis Worker)",
                lines=8,
                interactive=False,
                elem_classes=["result-box"],
            )

        with gr.Tab("📚 Sources"):
            sources_out = gr.Textbox(
                label="Sources",
                lines=5,
                interactive=False,
                elem_classes=["result-box"],
            )

        with gr.Tab("🔧 Policy Result (JSON)"):
            policy_out = gr.Code(
                label="Policy Result",
                language="json",
                lines=10,
                interactive=False,
            )

        with gr.Tab("📜 History / Trace Log"):
            history_out = gr.Textbox(
                label="Execution History",
                lines=15,
                interactive=False,
                elem_classes=["result-box"],
            )

    # Hidden outputs dùng nội bộ nếu cần
    route_state   = gr.State("")
    workers_state = gr.State("")

    # ── Wire up events ───────────────────────────────────────────────────────
    sample_dropdown.change(
        fn=fill_from_sample,
        inputs=[sample_dropdown],
        outputs=[query_input],
    )

    run_btn.click(
        fn=run_query,
        inputs=[query_input, save_cb],
        outputs=[
            summary_out,
            reason_out,
            answer_out,
            sources_out,
            policy_out,
            history_out,
            route_state,
            workers_state,
        ],
    )

    # Cho phép Enter trong textbox cũng trigger run
    query_input.submit(
        fn=run_query,
        inputs=[query_input, save_cb],
        outputs=[
            summary_out,
            reason_out,
            answer_out,
            sources_out,
            policy_out,
            history_out,
            route_state,
            workers_state,
        ],
    )

    gr.Markdown(
        """
---
<small>⚙️ Trace được lưu vào `./artifacts/traces/` nếu bật tuỳ chọn lưu.  
Powered by **LangGraph** + **Gradio**.</small>
        """
    )


if __name__ == "__main__":
    demo.launch(share=False, show_error=True)