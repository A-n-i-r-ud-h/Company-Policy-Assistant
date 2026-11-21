"""Company Policy Assistant - Streamlit front end.

Run with:  streamlit run app.py
"""
import html

import streamlit as st

import config
from modules.chatbot import PolicyChatbot
from modules.document_processor import process_pdf
from modules.errors import DuplicateDocumentError, PolicyAssistantError, friendly_error
from modules.rag_chain import PolicyRAGChain
from modules.vector_store import PolicyVectorStore

st.set_page_config(page_title="Company Policy Assistant", page_icon="📘", layout="wide")

SUGGESTED_QUESTIONS = [
    "What is the annual leave entitlement?",
    "Explain the travel reimbursement policy.",
    "What is the procedure for applying for leave?",
    "What are the reimbursement eligibility criteria?",
]

CSS = """
<style>
.block-container {padding-top: 1.5rem; max-width: 980px;}
.app-header {background: linear-gradient(120deg, #0F2A5C 0%, #2563EB 100%); color: #fff;
             padding: 1.4rem 1.6rem; border-radius: 14px; margin-bottom: 1.2rem;}
.app-header h1 {color: #fff; margin: 0; font-size: 1.9rem; padding: 0;}
.app-header p {color: #DBEAFE; margin: .25rem 0 0 0; font-size: 1.02rem;}
.welcome {background: #fff; border: 1px solid #E2E8F0; border-radius: 12px;
          padding: 1rem 1.2rem; margin-bottom: 1rem;}
.welcome h3 {margin: 0 0 .3rem 0; font-size: 1.1rem;}
.welcome p {margin: 0; color: #475569;}
.src-label {font-size: .78rem; font-weight: 600; color: #64748B; letter-spacing: .04em;
            text-transform: uppercase; margin: .6rem 0 .25rem 0;}
.src-chip {display: inline-block; background: #DBEAFE; color: #1E3A8A; border-radius: 999px;
           padding: .2rem .7rem; margin: 0 .4rem .3rem 0; font-size: .85rem; font-weight: 500;}
.excerpt {background: #F1F5F9; border-left: 3px solid #2563EB; padding: .5rem .8rem;
          border-radius: 4px; font-size: .85rem; color: #334155; white-space: pre-wrap; margin-bottom: .5rem;}
.excerpt-title {font-weight: 600; font-size: .85rem; margin-bottom: .2rem;}
.doc-name {font-weight: 600; font-size: .9rem; word-break: break-all;}
.doc-meta {color: #64748B; font-size: .78rem;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------- resources
@st.cache_resource(show_spinner=False)
def get_vector_store(api_key: str) -> PolicyVectorStore:
    return PolicyVectorStore(api_key=api_key)


def init_state(store: PolicyVectorStore, api_key: str) -> None:
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = PolicyChatbot(store, PolicyRAGChain(store, api_key=api_key))
    st.session_state.setdefault("upload_key", 0)
    st.session_state.setdefault("report", None)
    st.session_state.setdefault("pending_question", None)


# ----------------------------------------------------------------- rendering
def render_sources(sources) -> None:
    if not sources:
        return
    chips = "".join(
        f'<span class="src-chip">📄 {html.escape(s.filename)} | '
        f'{"Page " + str(s.page) if s.page else "Page n/a"}</span>' for s in sources)
    st.markdown(f'<div class="src-label">Source</div>{chips}', unsafe_allow_html=True)
    with st.expander("View retrieved excerpts"):
        for s in sources:
            page = f"Page {s.page}" if s.page else "Page n/a"
            st.markdown(
                f'<div class="excerpt-title">{html.escape(s.filename)} | {page}</div>'
                f'<div class="excerpt">{html.escape(s.excerpt)}</div>', unsafe_allow_html=True)


def render_message(msg: dict) -> None:
    avatar = "🧑‍💼" if msg["role"] == "user" else "📘"
    with st.chat_message(msg["role"], avatar=avatar):
        if msg.get("error"):
            st.error(msg["content"], icon="⚠️")
        else:
            st.markdown(msg["content"])
            render_sources(msg.get("sources"))


# ------------------------------------------------------------- document ops
def process_uploads(store: PolicyVectorStore, files) -> dict:
    """Index each PDF independently so one bad file never stops the others."""
    report = {"added": [], "skipped": [], "failed": []}
    progress = st.progress(0.0, text="Starting…")
    for i, f in enumerate(files):
        progress.progress(i / len(files), text=f"Processing {f.name} ({i + 1}/{len(files)})…")
        try:
            chunks, info = process_pdf(f.name, f.getvalue())
            store.check_duplicate(info)
            store.add_document(chunks, info)
            report["added"].append(info)
        except DuplicateDocumentError as exc:
            report["skipped"].append(str(exc))
        except Exception as exc:
            report["failed"].append(f"{f.name}: {friendly_error(exc)}")
    progress.empty()
    return report


def render_report(report: dict | None) -> None:
    if not report:
        return
    if report["added"]:
        chunks = sum(d["chunks"] for d in report["added"])
        st.success(f"Processed {len(report['added'])} document(s) into {chunks} chunks.")
    for msg in report["skipped"]:
        st.warning(msg)
    for msg in report["failed"]:
        st.error(msg)


# ------------------------------------------------------------------- layout
def sidebar(store: PolicyVectorStore) -> None:
    with st.sidebar:
        st.markdown("## 📘 Company Policy Assistant")
        st.caption("AI-powered HR Policy Support")
        st.divider()

        st.markdown("#### Upload Policy PDFs")
        files = st.file_uploader("Select one or more PDF files", type=["pdf"],
                                 accept_multiple_files=True,
                                 key=f"uploader_{st.session_state.upload_key}",
                                 label_visibility="collapsed")
        if files:
            for f in files:
                st.caption(f"📄 {f.name}")
        if st.button("Process Documents", type="primary", disabled=not files, width="stretch"):
            with st.spinner("Reading PDFs and creating embeddings…"):
                st.session_state.report = process_uploads(store, files)
            st.session_state.upload_key += 1   # clears the uploader
            st.rerun()
        render_report(st.session_state.report)

        st.divider()
        docs = store.list_documents()
        st.markdown(f"#### Indexed Documents ({len(docs)})")
        if not docs:
            st.caption("No documents indexed yet.")
        for d in docs:
            c1, c2 = st.columns([5, 1])
            c1.markdown(f'<div class="doc-name">📄 {html.escape(d["filename"])}</div>'
                        f'<div class="doc-meta">{d["pages"]} pages · {d["chunks"]} chunks</div>',
                        unsafe_allow_html=True)
            with c2.popover("", icon=":material/delete:", help="Remove this document"):
                st.write(f"Remove **{d['filename']}** and all its chunks?")
                if st.button("Yes, remove", key=f"rm_{d['filename']}", type="primary"):
                    try:
                        store.remove_document(d["filename"])
                        st.session_state.report = None
                    except Exception as exc:
                        st.error(friendly_error(exc))
                    st.rerun()
        if docs:
            st.caption(f"Total chunks in database: {store.count_chunks()}")

        st.divider()
        if st.button("Clear chat", icon=":material/delete_sweep:", width="stretch"):
            st.session_state.chatbot.clear()
            st.rerun()

        with st.expander("How to use"):
            st.markdown(
                "1. Upload one or more policy PDFs.\n"
                "2. Click **Process Documents**.\n"
                "3. Ask a question in the chat box.\n"
                "4. Check the **Source** under each answer.\n\n"
                "Answers come only from the indexed documents.")


def main_page(store: PolicyVectorStore) -> None:
    chatbot: PolicyChatbot = st.session_state.chatbot
    has_docs = not store.is_empty()

    st.markdown('<div class="app-header"><h1>Company Policy Assistant</h1>'
                '<p>AI-powered HR Policy Support</p></div>', unsafe_allow_html=True)

    # chat_input is pinned to the bottom of the page wherever it is called; calling it first lets us
    # hide the welcome block as soon as the first question arrives.
    typed = st.chat_input("Ask a question about company policies…" if has_docs
                          else "Upload and process policy PDFs to start chatting",
                          disabled=not has_docs)
    question = typed or st.session_state.pending_question
    st.session_state.pending_question = None

    if not chatbot.messages and not question:
        st.markdown(
            '<div class="welcome"><h3>👋 Welcome</h3>'
            '<p>Ask questions about leave, travel and reimbursement. Answers are generated only from the '
            'policy PDFs you have indexed, and every answer shows the policy file and page it came from.</p>'
            '</div>', unsafe_allow_html=True)
        if not has_docs:
            st.info("Start by uploading policy PDFs in the sidebar and clicking **Process Documents**. "
                    "Demo files are in `data/sample_policies/`.")
        st.markdown("**Try asking:**")
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTED_QUESTIONS):
            if cols[i % 2].button(q, key=f"sugg_{i}", disabled=not has_docs, width="stretch"):
                st.session_state.pending_question = q
                st.rerun()

    for msg in chatbot.messages:
        render_message(msg)

    if question:
        try:
            with st.chat_message("user", avatar="🧑‍💼"):
                st.markdown(question)
            with st.chat_message("assistant", avatar="📘"):
                with st.spinner("Searching policies and preparing your answer…"):
                    reply = chatbot.ask(question)
                if reply.get("error"):
                    st.error(reply["content"], icon="⚠️")
                else:
                    st.markdown(reply["content"])
                    render_sources(reply.get("sources"))
        except PolicyAssistantError as exc:   # e.g. empty / too-long question
            st.warning(str(exc))


def main() -> None:
    api_key = config.get_api_key()
    if not api_key:
        st.markdown('<div class="app-header"><h1>Company Policy Assistant</h1>'
                    '<p>AI-powered HR Policy Support</p></div>', unsafe_allow_html=True)
        st.error("**Gemini API key not found.** Copy `.env.example` to `.env`, set `GOOGLE_API_KEY`, "
                 "and restart the app. Get a free key at https://aistudio.google.com/apikey")
        st.stop()

    try:
        store = get_vector_store(api_key)
    except Exception as exc:
        st.error(f"Could not open the document database: {friendly_error(exc)}")
        st.stop()

    init_state(store, api_key)
    sidebar(store)
    main_page(store)


main()
