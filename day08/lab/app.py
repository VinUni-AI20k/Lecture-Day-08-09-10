"""
app.py — RAG Question Testing UI
=================================
Layout:
  Left  : Câu hỏi + submit
  Right : Baseline vs Variant side-by-side

Chạy:
    streamlit run app.py
"""

import json
import os
import sys

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))
from rag_answer import rag_answer  # noqa: E402

# =============================================================================
# PAGE CONFIG
# =============================================================================

st.set_page_config(
    page_title="RAG Question Tester",
    page_icon="🔍",
    layout="wide",
)

st.markdown("""
<style>
    /* Dark base */
    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stMain"],
    .main .block-container {
        background-color: #0d0d0d !important;
        color: #e8e8e8 !important;
    }

    /* Sidebar (if used) */
    [data-testid="stSidebar"] { background-color: #111111 !important; }

    /* Text inputs & textareas */
    textarea, input[type="text"] {
        background-color: #1a1a1a !important;
        color: #e8e8e8 !important;
        border: 1px solid #333 !important;
        border-radius: 6px !important;
    }

    /* Primary button */
    [data-testid="stButton"] button[kind="primary"] {
        background-color: #ffffff !important;
        color: #000000 !important;
        border: none !important;
        font-weight: 600 !important;
    }
    [data-testid="stButton"] button[kind="primary"]:hover {
        background-color: #d4d4d4 !important;
    }

    /* Secondary buttons */
    [data-testid="stButton"] button {
        background-color: #1e1e1e !important;
        color: #e8e8e8 !important;
        border: 1px solid #333 !important;
        border-radius: 6px !important;
    }
    [data-testid="stButton"] button:hover {
        background-color: #2a2a2a !important;
        border-color: #555 !important;
    }

    /* Success / warning / error boxes */
    [data-testid="stSuccess"]  { background-color: #0f2417 !important; border-left: 3px solid #22c55e !important; }
    [data-testid="stWarning"]  { background-color: #1f1500 !important; border-left: 3px solid #f59e0b !important; }
    [data-testid="stError"]    { background-color: #1f0a0a !important; border-left: 3px solid #ef4444 !important; }
    [data-testid="stInfo"]     { background-color: #0a0f1f !important; border-left: 3px solid #3b82f6 !important; }

    /* Expanders */
    [data-testid="stExpander"] {
        background-color: #141414 !important;
        border: 1px solid #2a2a2a !important;
        border-radius: 6px !important;
    }
    [data-testid="stExpander"] summary {
        color: #aaa !important;
        font-size: 13px !important;
    }

    /* JSON viewer */
    [data-testid="stJson"] { background-color: #141414 !important; }

    /* Dividers */
    hr { border-color: #2a2a2a !important; }

    /* Caption / small text */
    .stCaption, [data-testid="stCaptionContainer"] { color: #666 !important; }

    /* Column pill-style header */
    .col-header {
        font-size: 13px;
        font-weight: 500;
        color: #888;
        background: #1a1a1a;
        border: 1px solid #2a2a2a;
        border-radius: 6px;
        padding: 6px 12px;
        margin-bottom: 12px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# CONSTANTS
# =============================================================================

BASELINE_CONFIG = {
    "retrieval_mode": "dense",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": False,
    "use_query_transform": False,
    "transform_strategy": "expansion",
    "dense_weight": 1.0,
    "sparse_weight": 0.0,
    "label": "Baseline — Dense",
}

VARIANT_CONFIG = {
    "retrieval_mode": "hybrid",
    "top_k_search": 10,
    "top_k_select": 3,
    "use_rerank": True,
    "use_query_transform": True,
    "transform_strategy": "expansion",
    "dense_weight": 0.6,
    "sparse_weight": 0.4,
    "label": "Variant — Hybrid + Rerank + QT",
}

# =============================================================================
# HEADER
# =============================================================================

st.title("RAG Question Tester")
st.caption("Baseline (dense) vs Variant (hybrid + rerank + query transform)")
st.divider()

# =============================================================================
# LAYOUT: LEFT = INPUT | RIGHT = RESULTS
# =============================================================================

col_input, col_results = st.columns([1, 2.4], gap="large")

with col_input:
    st.subheader("Question")
    query = st.text_area(
        label="query",
        placeholder="e.g. SLA xử lý ticket P1 là bao lâu?",
        height=130,
        label_visibility="collapsed",
    )
    submitted = st.button("Submit", use_container_width=True, type="primary")

with col_results:
    if not submitted or not query.strip():
        if submitted and not query.strip():
            st.warning("Please enter a question.")
        else:
            st.markdown('<p style="color:#444; margin-top:48px;">Results will appear here after submitting.</p>', unsafe_allow_html=True)
    else:
        col_base, col_var = st.columns(2, gap="medium")

        def render_col(col, config: dict, q: str):
            with col:
                st.markdown(
                    f'<div class="col-header">{config["label"]}</div>',
                    unsafe_allow_html=True,
                )
                st.caption(
                    f'{config["retrieval_mode"]} | rerank={config["use_rerank"]} | '
                    f'qt={config["use_query_transform"]} | '
                    f'd={config["dense_weight"]} / s={config["sparse_weight"]}'
                )

                with st.spinner("Running pipeline..."):
                    try:
                        result = rag_answer(
                            query=q,
                            retrieval_mode=config["retrieval_mode"],
                            top_k_search=config["top_k_search"],
                            top_k_select=config["top_k_select"],
                            use_rerank=config["use_rerank"],
                            use_query_transform=config["use_query_transform"],
                            transform_strategy=config["transform_strategy"],
                            dense_weight=config["dense_weight"],
                            sparse_weight=config["sparse_weight"],
                            verbose=False,
                        )
                        error = None
                    except Exception as e:
                        result = None
                        error = str(e)

                if error:
                    st.error(f"Pipeline error: {error}")
                    return

                answer = result["answer"]
                if answer == "Không đủ dữ liệu":
                    st.warning(f"⚠ Abstain: {answer}")
                else:
                    st.success(answer)

                sources = result.get("sources", [])
                if sources:
                    st.markdown("**Sources:**")
                    for src in sources:
                        st.markdown(f"- `{src}`")

                chunks = result.get("chunks_used", [])
                if chunks:
                    st.markdown(f"**Chunks ({len(chunks)}):**")
                    for i, chunk in enumerate(chunks, 1):
                        meta = chunk.get("metadata", {})
                        score = chunk.get("score", 0)
                        source = meta.get("source", "unknown")
                        section = meta.get("section", "")
                        text = chunk.get("text", "")

                        label = f"[{i}] {source}"
                        if section:
                            label += f"  {section}"
                        if score:
                            label += f"  {score:.3f}"

                        with st.expander(label):
                            st.text(text[:300] + ("..." if len(text) > 300 else ""))

        render_col(col_base, BASELINE_CONFIG, query.strip())
        render_col(col_var, VARIANT_CONFIG, query.strip())
