# STAGE 2 — Streamlit UI

Context: `core.py` is committed and working. Build the UI as a thin
client — import only from `core`, no pipeline logic in this file.

## Task

Write `app.py`:

1. Sidebar: text inputs for embedding model / chat model (defaults
   `nomic-embed-text` / `llama3.2`), sliders for chunk size, chunk
   overlap, top-k. Show which files are currently indexed. A "clear
   session" button that resets everything.

2. Main area:
   - `st.file_uploader` for `.txt`/`.md`/`.pdf`, multiple files.
   - "Build / Rebuild Index" button: runs `core.load_document` per file
     → `core.chunk_documents` → `core.get_embeddings` → `core.build_index`,
     stores the result in `st.session_state`. Wrap in try/except and show
     a clear error (mention checking Ollama is running) rather than a
     raw traceback if it fails. Show a spinner while running.
   - Question input + "Ask" button: builds a retriever from the stored
     FAISS index (`as_retriever(search_kwargs={"k": top_k})`), builds the
     chain via `core.build_rag_chain`, calls `core.ask`, appends to a
     `st.session_state` chat history list.
   - Render chat history newest-first: grounded answers show normally
     with an expander listing sources (source file, page, snippet);
     not-found answers render in an `st.info` box so they're visually
     distinct.

3. Must support uploading a completely different document set and
   rebuilding without any code change — this is inherent if you're only
   calling `core.py` functions, just don't hardcode anything
   document-specific.

## Acceptance criteria

- `python -c "import ast; ast.parse(open('app.py').read())"` — no syntax
  errors.
- If Ollama is running locally: `streamlit run app.py`, upload
  `sample_docs/company_handbook.txt` (create it now if it doesn't exist —
  a short realistic HR policy excerpt is enough), build index, ask a
  question, confirm an answer with sources appears. If Ollama isn't
  running in this environment, at minimum confirm the app boots and the
  upload/build UI renders without error, and note the live check as
  something the user must do themselves.

Commit: "Add Streamlit UI". Then move to `03_tests_and_readme.md`.
