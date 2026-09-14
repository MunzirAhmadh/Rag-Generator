# STAGE 1 — Core pipeline

Context: brief already given. Build everything in one file, `core.py`.
Do not create additional modules — keep this fast and flat.

## Task

Write `core.py` containing:

1. `load_document(file_bytes: bytes, filename: str) -> list[Document]`
   - `.pdf`: extract text per page with `pypdf`, one `Document` per page
     with non-empty text, `metadata={"source": filename, "page": n}`.
   - `.txt`/`.md`: decode as UTF-8, one `Document`,
     `metadata={"source": filename, "page": None}`.
   - Anything else: raise `ValueError`.
   - Empty/whitespace-only input returns `[]`, doesn't crash.

2. `chunk_documents(docs, chunk_size=800, chunk_overlap=150) -> list[Document]`
   - `RecursiveCharacterTextSplitter`, add `chunk_id` to metadata.

3. `get_embeddings(model="nomic-embed-text", base_url="http://localhost:11434")`
   → `OllamaEmbeddings`.

4. `build_index(chunks, embeddings) -> FAISS`
   → `FAISS.from_documents(chunks, embeddings)`. Fresh index every call.

5. `get_llm(model="llama3.2", base_url="http://localhost:11434")`
   → `ChatOllama(temperature=0)`.

6. A module-level constant `NOT_FOUND_SENTINEL` (the exact sentence from
   the brief) and a `SYSTEM_PROMPT`/`ChatPromptTemplate` instructing the
   model: answer ONLY from the numbered context blocks, cite with
   `[1]`/`[2]`, output the sentinel verbatim (nothing else) if the answer
   isn't present.

7. `format_docs(docs) -> str` — numbers chunks, includes source + page
   inline.

8. `build_rag_chain(retriever, llm)` — LCEL:
   ```
   RunnableParallel(docs=retriever, question=RunnablePassthrough())
     | RunnablePassthrough.assign(answer=<format_docs+prompt+llm+StrOutputParser chain>)
   ```
   so invoking with a question string returns `{"docs", "question", "answer"}`.

9. `AnswerResult` dataclass: `answer: str`, `is_grounded: bool`,
   `sources: list[dict]` (each with `source`, `page`, `snippet`).

10. `ask(chain, question: str) -> AnswerResult` — invokes the chain,
    checks for `NOT_FOUND_SENTINEL` in the output, packages sources only
    when grounded.

## Acceptance criteria (check before moving on — don't skip this)

- `python -c "import core"` succeeds with no syntax/import errors.
- Manually construct two fake `Document`s, build a chain with a
  `langchain_core.language_models.fake_chat_models.FakeListChatModel`
  returning a canned answer, call `ask()`, and print the result — confirm
  `is_grounded=True` and `sources` populated.
- Repeat with the fake LLM returning the sentinel — confirm
  `is_grounded=False` and `sources=[]`.

Commit: "Add core RAG pipeline (loading, chunking, FAISS, LCEL chain)".
Then move to `02_streamlit_ui.md`. Don't exceed ~15 minutes here — if
something's taking longer, simplify rather than debug deeply; there's a
buffer at the end.
