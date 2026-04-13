import streamlit as st
import time
import random
import traceback

def init_ui():
    """Initializes the Streamlit UI configuration and styling."""
    st.set_page_config(
        page_title="Neon AI Assistant",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    custom_css = """
    <style>
    /* Global background and text color */
    html, body {
        background-color: #020617 !important;
    }
    .stApp > header, [data-testid="stHeader"] {
        background-color: transparent !important;
        background: transparent !important;
    }
    .stApp {
        background: radial-gradient(circle at center, #0f172a 0%, #020617 100%) !important;
        color: #f8fafc;
    }

    /* Base text colors */
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #f8fafc !important;
    }

    /* Sidebar glassmorphism */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.4) !important;
        backdrop-filter: blur(15px) !important;
        -webkit-backdrop-filter: blur(15px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Fix the white bottom container issue in Light Mode */
    [data-testid="stBottomBlockContainer"], 
    [data-testid="stBottom"],
    [data-testid="stBottom"] > div,
    [data-testid="stAppViewContainer"],
    div[data-testid="stBottom"] > *,
    .stApp > header,
    footer {
        background: transparent !important;
        background-color: transparent !important;
    }

    /* Chat input box container and glow */
    [data-testid="stChatInputContainer"] {
        background-color: transparent !important;
        padding-bottom: 2rem !important;
    }

    /* Make the chat input box bright/white with black text */
    [data-testid="stChatInput"] {
        background: rgba(255, 255, 255, 0.95) !important; 
        backdrop-filter: blur(15px) !important;
        border: 2px solid rgba(56, 189, 248, 0.8) !important;
        border-radius: 30px !important;
        box-shadow: 0 0 20px rgba(56, 189, 248, 0.3) !important;
        transition: all 0.3s ease-in-out;
        padding-left: 0.5rem;
        padding-right: 0.5rem;
    }

    [data-testid="stChatInput"]:focus-within {
        background: #ffffff !important;
        border-color: #0ea5e9 !important;
        box-shadow: 0 0 25px rgba(14, 165, 233, 0.6) !important;
    }

    /* KILL the native Streamlit inner input bounds to prevent overlapping boxes */
    [data-testid="stChatInput"] > div,
    [data-testid="stChatInput"] [data-baseweb],
    [data-testid="stChatInput"] [data-baseweb] > div,
    [data-testid="stChatInput"] [class*="st-"] {
        background-color: transparent !important;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    /* Black text for user input */
    [data-testid="stChatInput"] textarea {
        color: #000000 !important;
        font-weight: 600 !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #64748b !important;
    }

    
    [data-testid="stChatInputSubmitButton"] {
        background: #38bdf8 !important;
        color: #020617 !important;
        border-radius: 50% !important;
        transition: all 0.2s ease;
    }
    [data-testid="stChatInputSubmitButton"]:hover {
        transform: scale(1.1);
        box-shadow: 0 0 15px rgba(56,189,248,0.6);
    }
    [data-testid="stChatInputSubmitButton"] svg {
        fill: #020617 !important;
    }

    /* Chat message bubbles */
    [data-testid="stChatMessage"] {
        animation: fadeIn 0.5s ease-out;
        margin-bottom: 1rem;
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Marker hiding */
    .user-msg-marker, .assistant-msg-marker {
        display: none;
    }

    /* User Message Styling */
    [data-testid="stChatMessage"]:has(.user-msg-marker) {
        flex-direction: row-reverse;
    }
    [data-testid="stChatMessage"]:has(.user-msg-marker) [data-testid="stChatMessageContent"] {
        background: linear-gradient(135deg, #0ea5e9, #38bdf8) !important;
        color: #FFFFFF !important;
        border-radius: 20px 4px 20px 20px;
        padding: 1rem 1.5rem;
        box-shadow: 0 4px 15px rgba(56, 189, 248, 0.2);
    }
    [data-testid="stChatMessage"]:has(.user-msg-marker) [data-testid="stChatMessageContent"] p {
        color: #FFFFFF !important;
    }
    [data-testid="stChatMessage"]:has(.user-msg-marker) [data-testid="stChatAvatar"] {
        margin-left: 1rem;
        margin-right: 0;
    }

    /* Assistant Message Styling */
    [data-testid="stChatMessage"]:has(.assistant-msg-marker) {
        flex-direction: row;
    }
    [data-testid="stChatMessage"]:has(.assistant-msg-marker) [data-testid="stChatMessageContent"] {
        background: rgba(15, 23, 42, 0.7) !important;
        color: #FFFFFF !important;
        border: 1px solid rgba(56, 189, 248, 0.3);
        border-radius: 4px 20px 20px 20px;
        padding: 1rem 1.5rem;
        box-shadow: 0 0 15px rgba(56, 189, 248, 0.1);
        backdrop-filter: blur(10px);
    }
    [data-testid="stChatMessage"]:has(.assistant-msg-marker) [data-testid="stChatMessageContent"] p {
        color: #e2e8f0 !important;
    }
    [data-testid="stChatMessage"]:has(.assistant-msg-marker) [data-testid="stChatAvatar"] {
        margin-right: 1rem;
    }

    /* Title neon effect */
    h1 {
        text-shadow: 0 0 15px rgba(56, 189, 248, 0.4);
        background: linear-gradient(to right, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        margin-bottom: -0.5rem !important;
    }

    /* -------------------------------------
       THINKING PANEL / ST.STATUS / EXPANDERS 
       ------------------------------------- */
    /* Target the main wrapper regardless of whether it is stStatusWidget or generic details */
    [data-testid="stStatusWidget"],
    [data-testid="stChatMessage"] details {
        border: 1px solid rgba(34, 197, 94, 0.6) !important;
        border-radius: 8px !important;
        box-shadow: 0 0 15px rgba(34, 197, 94, 0.2) !important;
        overflow: hidden !important;
        background: #091022 !important;
        background-color: #091022 !important;
    }
    
    /* Absolute carpet-bombing of the white background on all summary/header children */
    [data-testid="stChatMessage"] details summary,
    [data-testid="stChatMessage"] details summary:hover,
    [data-testid="stChatMessage"] details summary:focus,
    [data-testid="stChatMessage"] details summary:active,
    [data-testid="stChatMessage"] details summary * {
        background: #091022 !important;
        background-color: #091022 !important;
        border-bottom: none !important;
        box-shadow: none !important;
    }
    
    /* Nuke Streamlit's white backgrounds in the details BODY (expander content) */
    [data-testid="stChatMessage"] details div {
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Code blocks inside details (like JSON debug info) */
    [data-testid="stChatMessage"] details pre,
    [data-testid="stChatMessage"] details code {
        background: #020617 !important;
        background-color: #020617 !important;
        color: #ef4444 !important;
        border: 1px solid rgba(239, 68, 68, 0.3) !important;
        border-radius: 6px !important;
        text-shadow: none !important;
    }

    /* Error UI */
    .error-card {
        background: #091022 !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(239, 68, 68, 0.8) !important;
        border-radius: 8px !important;
        padding: 1.5rem;
        box-shadow: 0 0 15px rgba(239, 68, 68, 0.3) !important;
        margin-bottom: 1rem;
        animation: fadeIn 0.4s ease-out;
    }
    .error-card-title {
        color: #ef4444 !important;
        font-size: 1.25rem;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 5px rgba(239, 68, 68, 0.3);
    }
    .error-card-msg {
        color: #fca5a5 !important;
    }
    
    /* Expander inside Error */
    [data-testid="stExpander"] {
        background: #091022 !important;
        border: 1px solid rgba(34, 197, 94, 0.6) !important;
        border-radius: 8px !important;
        backdrop-filter: blur(5px) !important;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: rgba(2, 6, 23, 0.5);
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(56, 189, 248, 0.3);
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(56, 189, 248, 0.6);
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)


def yield_thinking_logs(query: str):
    """
    Mock agent logic: Generates thinking steps.
    """
    reasoning_steps = [
        "Analyzing user query structure...",
        f"Extracting key intent from: '{query[:15]}...'",
        "Consulting vector embeddings and knowledge base...",
        "Identifying relevant components (Glassmorphism, Streamlit State)...",
        "Synthesizing the final intelligent response...",
    ]
    for step in reasoning_steps:
        time.sleep(random.uniform(0.4, 0.9))
        yield step


def yield_streaming_response(query: str):
    """
    Mock agent logic: Generates a response token by token.
    """
    error_trigger = "error" in query.lower()
    
    if error_trigger:
        time.sleep(1)
        raise ConnectionError("Mock Connection Error: Lost connect to inference server at port 8000.")

    base_response = (
        f"You said: **{query}**.\n\n"
        "Here is the modern, visually impressive chatbot UI you requested. "
        "It features **Glassmorphism**, neon typography, and a *gradient dark theme* to look very sleek.\n"
        "- **Sidebar Configuration**: Manage parameters via the side panel."
        "\n- **Thinking Panel**: I stream my logs live inside the expander above before answering."
        "\n- **Streaming Response**: Tokens are printed word-by-word just like ChatGPT."
        "\n\n*Try asking me something else, or type `error` to see the error handling UI!*"
    )
    
    tokens = base_response.split(" ")
    for token in tokens:
        time.sleep(random.uniform(0.02, 0.08))
        yield token + " "


def render_sidebar():
    """Renders the settings sidebar."""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        st.subheader("Model")
        st.selectbox("Model Selection", ["Neon-Chat-v1", "Neon-Reason-v2", "GPT-Simulator"], index=0, label_visibility="collapsed")
        
        st.divider()
        
        st.subheader("Parameters")
        st.slider("Temperature", 0.0, 1.0, 0.7, 0.01)
        st.slider("Max Tokens", 100, 4000, 1000, step=100)
        
        st.divider()
        
        st.checkbox("Enable Web Search", value=True)
        
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<div style='color: #94a3b8; font-size: 0.9rem;'>"
            "💡 <b>Tip:</b> Type <code>error</code> in the chat to test the debug/error handling section."
            "</div>", unsafe_allow_html=True
        )


def main():
    init_ui()
    render_sidebar()
    
    st.title("⚡ CyberAssist AI")
    st.markdown("<p style='color: #94a3b8;'><i>Your intelligent AI assistant wrapped in a sleek, modern interface.</i></p>", unsafe_allow_html=True)
    
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I am CyberAssist. How can I help you today?"}
        ]

    for msg in st.session_state.messages:
        avatar_icon = "⚡" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar_icon):
            if msg["role"] == "user":
                st.markdown("<div class='user-msg-marker'></div>", unsafe_allow_html=True)
            else:
                st.markdown("<div class='assistant-msg-marker'></div>", unsafe_allow_html=True)
            st.markdown(msg["content"])

    if prompt := st.chat_input("Enter your message to CyberAssist..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown("<div class='user-msg-marker'></div>", unsafe_allow_html=True)
            st.markdown(prompt)

        with st.chat_message("assistant", avatar="⚡"):
            st.markdown("<div class='assistant-msg-marker'></div>", unsafe_allow_html=True)
            try:
                with st.status("🧠 Thinking Process...", expanded=True) as status:
                    for step_log in yield_thinking_logs(prompt):
                        st.write(f"→ {step_log}")
                    status.update(label="🧠 Thought process complete", state="complete", expanded=False)

                full_response = st.write_stream(yield_streaming_response(prompt))
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
            except Exception as e:
                # Custom Error UI
                st.markdown(
                    '''
                    <div class="error-card">
                        <div class="error-card-title">⚠️ Something went wrong</div>
                        <div class="error-card-msg">An unexpected error occurred while processing your request. Please try again.</div>
                    </div>
                    ''',
                    unsafe_allow_html=True
                )
                with st.expander("🔧 Debug Details", expanded=False):
                    error_details = traceback.format_exc()
                    st.code(error_details, language="python")

if __name__ == "__main__":
    main()
