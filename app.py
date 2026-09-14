import streamlit as st
import tempfile
import os
from core import RAGPipeline, RAGResult


st.set_page_config(page_title="RAG Generator", page_icon="📚", layout="wide")


def init_session_state():
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = RAGPipeline()
    if "index_built" not in st.session_state:
        st.session_state.index_built = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def save_uploaded_files(uploaded_files) -> list[str]:
    paths = []
    for uploaded_file in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(uploaded_file.name)[1]) as tmp:
            tmp.write(uploaded_file.getbuffer())
            paths.append(tmp.name)
    return paths


def build_index(file_paths: list[str]):
    with st.spinner("Building index..."):
        st.session_state.pipeline.build_index(file_paths)
        st.session_state.index_built = True
        st.success("Index built successfully!")


def display_citations(citations: list):
    if not citations:
        return
    with st.expander("Citations", expanded=False):
        for i, cit in enumerate(citations, 1):
            page_str = f", page {cit.page}" if cit.page else ""
            st.markdown(f"**{i}. {cit.filename}{page_str}**")
            st.caption(cit.snippet)


def main():
    init_session_state()

    st.title("📚 RAG Generator")
    st.caption("Upload documents, build an index, and ask questions grounded in your data.")

    with st.sidebar:
        st.header("Configuration")
        embedding_model = st.text_input("Embedding Model", value="nomic-embed-text")
        generation_model = st.text_input("Generation Model", value="llama3.2")
        chunk_size = st.number_input("Chunk Size", value=1000, min_value=100, max_value=4000, step=100)
        chunk_overlap = st.number_input("Chunk Overlap", value=200, min_value=0, max_value=1000, step=50)

        if st.button("Update Pipeline Config"):
            st.session_state.pipeline = RAGPipeline(
                embedding_model=embedding_model,
                generation_model=generation_model,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
            st.session_state.index_built = False
            st.success("Pipeline configuration updated.")

        st.divider()
        st.header("Documents")
        uploaded_files = st.file_uploader(
            "Upload PDF or TXT files",
            type=["pdf", "txt"],
            accept_multiple_files=True,
        )

        if uploaded_files and st.button("Build Index", type="primary"):
            file_paths = save_uploaded_files(uploaded_files)
            try:
                build_index(file_paths)
            finally:
                for p in file_paths:
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

        if st.session_state.index_built:
            st.success("✅ Index ready")
        else:
            st.info("Upload documents and click Build Index")

    if not st.session_state.index_built:
        st.info("👈 Upload documents and build the index to start asking questions.")
        return

    st.divider()

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg["role"] == "assistant" and "result" in msg:
                display_citations(msg["result"].citations)
                if not msg["result"].is_grounded:
                    st.warning("⚠️ Answer not grounded in documents")

    if question := st.chat_input("Ask a question about your documents..."):
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result: RAGResult = st.session_state.pipeline.query(question)
            st.markdown(result.answer)
            display_citations(result.citations)
            if not result.is_grounded:
                st.warning("⚠️ Answer not grounded in documents")

        st.session_state.chat_history.append({"role": "assistant", "content": result.answer, "result": result})


if __name__ == "__main__":
    main()