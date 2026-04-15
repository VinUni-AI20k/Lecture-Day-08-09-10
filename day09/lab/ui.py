"""
ui.py — Streamlit UI để test Day 09 Multi-Agent Pipeline
Chạy: streamlit run ui.py
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
import json
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Day 09 — Multi-Agent Pipeline",
    page_icon="🤖",
    layout="wide",
)

st.title("🤖 Multi-Agent Pipeline — Day 09")
st.caption("Supervisor-Worker · MCP · Trace & Observability")

# ── Graph visualization (always visible) ─────────────────────────────────────
graph_img = os.path.join(os.path.dirname(__file__), "artifacts", "graph_visualization.png")
if os.path.exists(graph_img):
    with st.expander("🗺 Pipeline Graph", expanded=False):
        st.image(graph_img, caption="Supervisor-Worker Graph (LangGraph)", use_container_width=True)

# ── Load pipeline (cached) ────────────────────────────────────────────────────
@st.cache_resource(show_spinner="Loading pipeline...")
def load_pipeline():
    from graph import run_graph
    return run_graph

run_graph = load_pipeline()

# ── Sidebar: sample questions ─────────────────────────────────────────────────
st.sidebar.header("📋 Câu hỏi mẫu")
samples = {
    "🟡 SLA P1 escalation":      "Ticket P1 lúc 2am — escalation xảy ra thế nào và ai nhận thông báo?",
    "🔴 Flash Sale hoàn tiền":   "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất trong 7 ngày — được không?",
    "🔴 Level 3 khẩn cấp":       "Contractor cần Admin Access Level 3 để sửa P1 khẩn cấp — quy trình tạm thời là gì?",
    "🟢 Store credit":            "Store credit bằng bao nhiêu % tiền gốc?",
    "🟢 Đổi mật khẩu":           "Mật khẩu phải đổi sau bao nhiêu ngày và cảnh báo trước mấy ngày?",
    "🟡 Nhân viên thử việc":     "Nhân viên thử việc muốn làm remote — điều kiện là gì?",
    "⚫ Abstain (không có data)": "Mức phạt tài chính khi vi phạm SLA P1 là bao nhiêu?",
    "🟡 ERR-9999 HITL":          "Hệ thống báo lỗi ERR-9999 không rõ nguyên nhân, khẩn cấp cần xử lý",
}

selected = st.sidebar.radio("Chọn câu hỏi:", list(samples.keys()))
if st.sidebar.button("Dùng câu này", use_container_width=True):
    st.session_state["question"] = samples[selected]

st.sidebar.divider()
st.sidebar.markdown("**Routing legend:**")
st.sidebar.markdown("🔵 `retrieval_worker`\n🟠 `policy_tool_worker`\n🔴 `human_review`")

# ── Main input ────────────────────────────────────────────────────────────────
question = st.text_area(
    "Nhập câu hỏi:",
    value=st.session_state.get("question", ""),
    height=80,
    placeholder="VD: Ticket P1 lúc 2am — ai nhận thông báo đầu tiên?",
)

run_btn = st.button("▶ Chạy pipeline", type="primary", use_container_width=True)

# ── Run & display ─────────────────────────────────────────────────────────────
if run_btn and question.strip():
    with st.spinner("Đang xử lý..."):
        try:
            result = run_graph(question.strip())
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

    # Route badge
    route = result.get("supervisor_route", "")
    route_colors = {
        "retrieval_worker":    "🔵",
        "policy_tool_worker":  "🟠",
        "human_review":        "🔴",
    }
    badge = route_colors.get(route, "⚪")

    # HITL banner
    if result.get("hitl_triggered"):
        st.warning("⚠️ **HITL TRIGGERED** — Unknown error code + high risk context. Human review required before proceeding.")

    # ── Row 1: Answer + Metadata ──────────────────────────────────────────────
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("💬 Câu trả lời")
        answer = result.get("final_answer", "")
        if "SYNTHESIS ERROR" in answer or "PIPELINE_ERROR" in answer:
            st.error(answer)
        elif "Không đủ thông tin" in answer or result.get("confidence", 1) < 0.35:
            st.warning(f"⚠️ **Abstain** — {answer}")
        else:
            st.success(answer)

    with col2:
        st.subheader("📊 Metadata")
        conf = result.get("confidence", 0)
        st.metric("Confidence", f"{conf:.0%}", delta=None)
        st.metric("Latency", f"{result.get('latency_ms', 0):,} ms")

        st.markdown(f"**Route:** {badge} `{route}`")
        st.caption(f"**Reason:** {result.get('route_reason', '')}")

        sources = result.get("retrieved_sources", [])
        if sources:
            st.markdown("**Sources:**")
            for s in sources:
                st.caption(f"📄 {s}")

    # ── Row 2: MCP + Workers ──────────────────────────────────────────────────
    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("🔧 MCP Tools Called")
        mcp_calls = result.get("mcp_tools_used", [])
        if mcp_calls:
            for call in mcp_calls:
                with st.expander(f"🛠 `{call['tool']}` — {call.get('timestamp','')[:19]}"):
                    st.json({
                        "input":  call.get("input"),
                        "output": call.get("output"),
                        "error":  call.get("error"),
                    })
        else:
            st.info("Không có MCP tool được gọi")

    with col4:
        st.subheader("🔄 Execution Flow")
        workers = result.get("workers_called", [])
        worker_icons = {
            "retrieval_worker":   "🔍",
            "policy_tool_worker": "📋",
            "synthesis_worker":   "✍️",
            "human_review":       "👤",
        }
        flow = " → ".join([f"{worker_icons.get(w,'⚙️')} `{w}`" for w in workers])
        st.markdown(flow)

        st.markdown("**History:**")
        for h in result.get("history", []):
            st.caption(f"• {h}")

    # ── Row 3: Full trace ─────────────────────────────────────────────────────
    st.divider()
    with st.expander("🗂 Full Trace JSON"):
        # Exclude large fields for readability
        trace_display = {k: v for k, v in result.items() if k != "retrieved_chunks"}
        st.json(trace_display)

    with st.expander("📦 Retrieved Chunks"):
        chunks = result.get("retrieved_chunks", [])
        if chunks:
            for i, c in enumerate(chunks, 1):
                st.markdown(f"**[{i}]** `{c.get('source')}` — score: `{c.get('score', 0):.3f}`")
                st.caption(c.get("text", "")[:300])
                st.divider()
        else:
            st.info("Không có chunks")

elif run_btn:
    st.warning("Vui lòng nhập câu hỏi.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("Team 62 · Lab Day 09 · Multi-Agent Orchestration · 2026-04-14")
