
import streamlit as st

from src.export import transcript_markdown
from src.llm import (
    DEFAULT_MODELS,
    build_qa_prompt,
    build_summary_prompt,
    configure,
    get_token,
    stream_response,
)
from src.pdf_utils import extract_pdf, file_hash

st.set_page_config(page_title="PDF Summarizer Chatbot", page_icon="🖊️", layout="wide")

# ---------------- Session state ----------------
ms = st.session_state
if "messages" not in ms:
    ms.messages = [{"role": "assistant", "content": "Upload one or more PDFs in the sidebar to get started."}]
if "documents" not in ms:
    ms.documents = {}  # name -> extracted doc dict
if "active_doc" not in ms:
    ms.active_doc = None
if "gen" not in ms:
    ms.gen = {"model": next(iter(DEFAULT_MODELS.values())),
              "temperature": 0.1, "top_p": 0.9, "max_length": 2000}


def active_doc():
    if ms.active_doc and ms.active_doc in ms.documents:
        return ms.documents[ms.active_doc]
    return None


# ---------------- Sidebar ----------------
with st.sidebar:
    st.title("🖊️ PDF Summarizer Chatbot")

    # Token
    token = get_token()
    if token:
        configure(token)
        st.success("Gemini API key ready", icon="✅")
    else:
        entered = st.text_input("Gemini API key", type="password",
                                 help="Get one at https://aistudio.google.com/apikey")
        if entered:
            configure(entered)
            token = entered
        if not token:
            st.warning("Enter a valid Gemini API key.", icon="⚠️")

    st.divider()

    # Uploader (multi)
    uploaded = st.file_uploader("Upload PDF(s)", type="pdf", accept_multiple_files=True)
    if uploaded:
        for f in uploaded:
            h = file_hash(f)
            key = f"{f.name}#{h}"
            if key not in ms.documents:
                with st.spinner(f"Extracting {f.name}..."):
                    doc = extract_pdf(f)
                doc["hash"] = h
                ms.documents[key] = doc
                if ms.active_doc is None:
                    ms.active_doc = key
        # activate newly uploaded? keep current if valid
        if ms.active_doc not in ms.documents and ms.documents:
            ms.active_doc = next(iter(ms.documents.keys()))

    if ms.documents:
        st.subheader("Documents")
        labels = {k: f"{v['name']}  ({v.get('page_count', '?')}p, {v.get('word_count', '?')}w)"
                  for k, v in ms.documents.items()}
        ms.active_doc = st.selectbox(
            "Active document", list(ms.documents.keys()),
            index=list(ms.documents.keys()).index(ms.active_doc) if ms.active_doc in ms.documents else 0,
            format_func=lambda k: labels.get(k, k),
        )
        doc = active_doc()
        if doc and not doc.get("ok"):
            st.error(doc.get("error", "Failed to extract."))
        elif doc:
            st.caption(f"Pages: {doc['page_count']} · Words: {doc['word_count']}")

        if st.button("Remove active document"):
            if ms.active_doc in ms.documents:
                del ms.documents[ms.active_doc]
            ms.active_doc = next(iter(ms.documents.keys())) if ms.documents else None
            st.rerun()

    st.divider()

    # Summarization
    with st.expander("🧾 Summarization", expanded=False):
        fmt = st.selectbox("Format", ["paragraph", "bullet", "executive"], index=0)
        length = st.selectbox("Length", ["short", "medium", "long"], index=1)
        language = st.selectbox("Language", ["English", "Spanish", "French", "German", "Hindi"], index=0)
        if st.button("Generate summary", type="primary"):
            doc = active_doc()
            if not doc or not doc.get("ok"):
                st.error("Upload a valid PDF first.")
            else:
                prompt = build_summary_prompt(doc["text"], fmt, length, language)
                st.session_state["_pending_summary"] = (prompt, doc["name"])

    st.divider()

    # Generation settings
    with st.expander("⚙️ Generation settings", expanded=False):
        model_label = st.selectbox("Model", list(DEFAULT_MODELS.keys()), index=0)
        ms.gen["model"] = DEFAULT_MODELS[model_label]
        ms.gen["temperature"] = st.slider("Temperature", 0.0, 1.0, ms.gen["temperature"], 0.05)
        ms.gen["top_p"] = st.slider("Top p", 0.1, 1.0, ms.gen["top_p"], 0.05)
        ms.gen["max_length"] = st.slider("Max length", 256, 4000, ms.gen["max_length"], 64)

    st.divider()
    if st.button("Clear chat history"):
        ms.messages = [{"role": "assistant", "content": "Chat cleared. Upload/ select a document to continue."}]
        st.rerun()

    st.markdown("---")
    st.caption("Developed by Ichikawa Hiroshi · 2024")
    st.markdown('<a href="https://github.com/0xichikawa" target="_blank">GitHub</a>',
                unsafe_allow_html=True)


# ---------------- Main ----------------
st.title("🖊️ PDF Summarizer Chatbot")

doc = active_doc()
if doc and doc.get("ok"):
    st.info(f"Active: **{doc['name']}** — {doc['page_count']} pages · {doc['word_count']} words")

# Handle pending summary (generate + store + show)
if "_pending_summary" in ms:
    prompt, doc_name = ms.pop("_pending_summary")
    st.subheader("Summary")
    ph = st.empty()
    full = ""
    try:
        out = stream_response(ms.gen["model"], prompt, ms.gen["temperature"], ms.gen["top_p"], ms.gen["max_length"])
        # stream_response may return list OR generator
        if isinstance(out, list):
            for item in out:
                full += item
                ph.markdown(full)
        else:
            for item in out:
                full += item
                ph.markdown(full)
        ph.markdown(full)
    except Exception as exc:
        st.error(f"Summary generation failed: {exc}")
        full = ""
    if full:
        st.download_button("Download summary (.md)", data=full.encode("utf-8"),
                           file_name=f"summary_{doc_name}.md", mime="text/markdown")
        ms.messages.append({"role": "assistant", "content": f"**Summary of {doc_name}:**\n\n{full}"})

# Chat history display
for message in ms.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

# Export chat
if len(ms.messages) > 1:
    with st.expander("Export chat", expanded=False):
        if st.button("Prepare Markdown transcript"):
            md = transcript_markdown(ms.messages, (doc["name"] if doc else "document"))
            st.download_button("Download transcript (.md)", data=md.encode("utf-8"),
                              file_name="chat_transcript.md", mime="text/markdown")

# Chat input
if not ms.documents:
    st.info("👈 Upload a PDF from the sidebar to begin.")
else:
    question = st.chat_input("Ask a question about the document...")
    if question:
        ms.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        d = active_doc()
        # Build page-aware context
        if d and d.get("ok"):
            pages = d.get("pages", [])
            # Use all pages but cap total chars
            ctx_parts = []
            used = 0
            CAP = 16000
            for p in pages:
                chunk = f"[p.{p['page']}] {p['text']}"
                if used + len(chunk) > CAP:
                    chunk = chunk[: CAP - used]
                ctx_parts.append(chunk)
                used += len(chunk)
                if used >= CAP:
                    break
            context = "\n\n".join(ctx_parts)
        else:
            context = ""

        prompt = build_qa_prompt(context, question, ms.messages[:-1])
        with st.chat_message("assistant"), st.spinner("Thinking..."):
            ph = st.empty()
            full = ""
            try:
                out = stream_response(ms.gen["model"], prompt, ms.gen["temperature"],
                                     ms.gen["top_p"], ms.gen["max_length"])
                for item in out:
                    full += item
                    ph.markdown(full)
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
                full = f"_Error: {exc}_"
            ph.markdown(full)
        ms.messages.append({"role": "assistant", "content": full})
