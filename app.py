import streamlit as st
from core import (
    load_document,
    chunk_documents,
    get_embeddings,
    build_index,
    get_llm,
    build_rag_chain,
    ask,
    AnswerResult,
    NOT_FOUND_SENTINEL,
)


st.set_page_config(page_title="RAG Generator", page_icon="📚", layout="wide")


def init_session_state():
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = None
    if "chain" not in st.session_state:
        st.session_state.chain = None
    if "index_built" not in st.session_state:
        st.session_state.index_built = False
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "embed_model" not in st.session_state:
        st.session_state.embed_model = "nomic-embed-text"
    if "gen_model" not in st.session_state:
        st.session_state.gen_model = "llama3.2"
    if "chunk_size" not in st.session_state:
        st.session_state.chunk_size = 800
    if "chunk_overlap" not in st.session_state:
        st.session_state.chunk_overlap = 150
    if "top_k" not in st.session_state:
        st.session_state.top_k = 4
    if "indexed_files" not in st.session_state:
        st.session_state.indexed_files = []


def build_index_from_files(uploaded_files):
    try:
        with st.spinner("Building index..."):
            all_docs = []
            file_names = []
            for uploaded_file in uploaded_files:
                file_bytes = uploaded_file.getbuffer()
                docs = load_document(file_bytes, uploaded_file.name)
                all_docs.extend(docs)
                file_names.append(uploaded_file.name)

            chunks = chunk_documents(all_docs, st.session_state.chunk_size, st.session_state.chunk_overlap)
            embeddings = get_embeddings(model=st.session_state.embed_model)
            vectorstore = build_index(chunks, embeddings)
            llm = get_llm(model=st.session_state.gen_model)
            retriever = vectorstore.as_retriever(search_kwargs={"k": st.session_state.top_k})
            chain = build_rag_chain(retriever, llm)

            st.session_state.vectorstore = vectorstore
            st.session_state.chain = chain
            st.session_state.index_built = True
            st.session_state.indexed_files = file_names
            st.success("Index built successfully!")
    except Exception as e:
        st.error(f"Failed to build index: {e}\n\nMake sure Ollama is running (`ollama serve`) and the models are pulled (`ollama pull nomic-embed-text` and `ollama pull llama3.2`).")


def clear_session():
    st.session_state.vectorstore = None
    st.session_state.chain = None
    st.session_state.index_built = False
    st.session_state.chat_history = []
    st.session_state.indexed_files = []
    st.success("Session cleared.")


def display_sources(sources: list):
    if not sources:
        return
    with st.expander("Sources", expanded=False):
        for i, src in enumerate(sources, 1):
            page_str = f", page {src['page']}" if src["page"] is not None else ""
            st.markdown(f"**{i}. {src['source']}{page_str}**")
            st.caption(src["snippet"])


def main():
    init_session_state()

    st.title("📚 RAG Generator")
    st.caption("Upload documents, build an index, and ask questions grounded in your data.")

    with st.sidebar:
        st.header("Configuration")
        embed_model = st.text_input("Embedding Model", value=st.session_state.embed_model)
        gen_model = st.text_input("Generation Model", value=st.session_state.gen_model)
        chunk_size = st.number_input("Chunk Size", value=st.session_state.chunk_size, min_value=100, max_value=4000, step=100)
        chunk_overlap = st.number_input("Chunk Overlap", value=st.session_state.chunk_overlap, min_value=0, max_value=1000, step=50)
        top_k = st.slider("Top-K Retrieval", min_value=1, max_value=20, value=st.session_state.top_k, step=1)

        if st.button("Update Config"):
            st.session_state.embed_model = embed_model
            st.session_state.gen_model = gen_model
            st.session_state.chunk_size = chunk_size
            st.session_state.chunk_overlap = chunk_overlap
            st.session_state.top_k = top_k
            st.session_state.index_built = False
            st.session_state.chain = None
            st.session_state.vectorstore = None
            st.success("Configuration updated. Rebuild index to apply.")

        st.divider()

        if st.session_state.indexed_files:
            st.header("Indexed Files")
            for f in st.session_state.indexed_files:
                st.caption(f"• {f}")

        st.header("Documents")
        uploaded_files = st.file_uploader(
            "Upload PDF, TXT, or MD files",
            type=["pdf", "txt", "md"],
            accept_multiple_files=True,
        )

        col1, col2 = st.columns(2)
        with col1:
            if uploaded_files and st.button("Build / Rebuild Index", type="primary", use_container_width=True):
                build_index_from_files(uploaded_files)
        with col2:
            if st.session_state.index_built and st.button("Clear Session", use_container_width=True):
                clear_session()

        if st.session_state.index_built:
            st.success("✅ Index ready")
        else:
            st.info("Upload documents and click Build / Rebuild Index")

    if not st.session_state.index_built:
        st.info("👈 Upload documents and build the index to start asking questions.")
        return

    st.divider()

    # Render chat history newest-first
    for msg in reversed(st.session_state.chat_history):
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and "result" in msg:
                result = msg["result"]
                if result.is_grounded:
                    st.markdown(result.answer)
                    display_sources(result.sources)
                else:
                    st.info(result.answer)
            else:
                st.markdown(msg["content"])

    if question := st.chat_input("Ask a question about your documents..."):
        st.session_state.chat_history.append({"role": "user", "content": question})

        with st.spinner("Thinking..."):
            result: AnswerResult = ask(st.session_state.chain, question)

        st.session_state.chat_history.append({"role": "assistant", "content": result.answer, "result": result})
        st.rerun()


if __name__ == "__main__":
    main()