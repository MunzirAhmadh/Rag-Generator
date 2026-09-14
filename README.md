# RAG Generator

A Retrieval-Augmented Generation application built with LangChain (LCEL), FAISS, Ollama, and Streamlit. Upload documents at runtime, build a vector index, and ask questions grounded in your data with structured citations and explicit "not found" handling.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DOCUMENT INDEXING                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   Upload PDF/TXT/MD  ──►  load_document()  ──►  chunk_documents()          │
│       (runtime)              (per page)           (800/150, chunk_id)       │
│                                                                      │       │
│                                                                      ▼       │
│                                                         get_embeddings()     │
│                                                            (nomic-embed-text)│
│                                                                      │       │
│                                                                      ▼       │
│                                                         build_index()        │
│                                                            (FAISS)           │
│                                                                      │       │
│                                                                      ▼       │
│                                                      st.session_state.vectorstore  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            QUESTION ANSWERING                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   User Question  ──►  retriever (top-k)  ──►  Retrieved Documents           │
│                                                                              │
│                          │                          │                        │
│                          ▼                          ▼                        │
│                  format_docs()              build_rag_chain()               │
│                  (numbered,                  (RunnableParallel +            │
│                   source/page)               .assign() LCEL)                │
│                          │                          │                        │
│                          └──────────┬─────────────┘                        │
│                                     ▼                                        │
│                    ┌────────────────────────────┐                           │
│                    │       LLM (llama3.2)       │                           │
│                    │  SYSTEM_PROMPT:            │                           │
│                    │  - Answer ONLY from context│                           │
│                    │  - Cite with [1], [2]      │                           │
│                    │  - Output sentinel if      │                           │
│                    │    not found               │                           │
│                    └──────────────┬─────────────┘                           │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌────────────────────────────┐                           │
│                    │      ask() function        │                           │
│                    │  - Checks for sentinel     │                           │
│                    │  - Returns AnswerResult:   │                           │
│                    │    {answer, is_grounded,   │                           │
│                    │     sources: [{source,     │                           │
│                    │       page, snippet}]}     │                           │
│                    └────────────────────────────┘                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- **Python 3.10+**
- **Ollama** running locally with models:
  - `nomic-embed-text` (embeddings)
  - `llama3.2` (generation)

---

## Setup & Run

```bash
# Clone and navigate
cd Rag-Generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Pull Ollama models (in separate terminal, keep running)
ollama serve
ollama pull nomic-embed-text
ollama pull llama3.2

# Run the Streamlit app
streamlit run app.py
```

Open http://localhost:8501 in your browser.

---

## Running Tests (Fully Offline)

```bash
pytest tests/ -v
```

**All tests run offline** — no network calls, no Ollama required. Uses `FakeEmbeddings` (deterministic hash-based vectors) and `FakeListChatModel` for LLM responses.

---

## Usage Walkthrough

### 1. Start the App
- Run `streamlit run app.py`
- Sidebar shows configuration defaults (embedding: `nomic-embed-text`, generation: `llama3.2`)

### 2. Load Company Handbook (sample_docs/company_handbook.txt)
- Click "Browse files" → select `sample_docs/company_handbook.txt`
- Click **"Build / Rebuild Index"**
- Wait for "Index built successfully!" and "✅ Index ready"
- Sidebar shows "Indexed Files: • company_handbook.txt"

### 3. Ask Questions About Handbook
| Question | Expected |
|----------|----------|
| "What are the standard work hours?" | Grounded answer citing handbook.txt, page 1 |
| "How many vacation days do employees get?" | Grounded answer citing handbook.txt, page 2 |
| "What is the remote work policy?" | Grounded answer citing handbook.txt, page 2 |

### 4. Swap to Product FAQ (sample_docs/product_faq.txt)
- Click **"Clear Session"** (resets everything)
- Upload `sample_docs/product_faq.txt`
- Click **"Build / Rebuild Index"**

### 5. Ask Questions About Product FAQ
| Question | Expected |
|----------|----------|
| "How much is the Professional tier?" | Grounded answer: "$29/user/month" citing faq.txt |
| "What integrations are available?" | Grounded answer listing Slack, Teams, etc. |
| "What is the API rate limit for Professional?" | Grounded answer: "1,000 requests/hour" |

### 6. Demonstrate Not-Found Path
Ask any question **not covered by the loaded documents**, e.g.:
- "What is the CEO's salary?" (handbook loaded)
- "What is the weather in Tokyo?" (FAQ loaded)
- "How do I bake a cake?" (any doc set)

**Result:** Answer renders in a blue `st.info` box with the exact sentinel text:
> "I don't have enough information in the provided documents to answer that."
> `is_grounded=False`, `sources=[]`

---

## Definition of Done Checklist (from 00_BRIEF.md)

- ✅ Upload a PDF or TXT at runtime, build the index, no code edits required
- ✅ Chunking works and is configurable (chunk size, overlap via sidebar)
- ✅ FAISS retrieval actually returns relevant chunks
- ✅ The LCEL chain gives a grounded answer with citations (source, page, snippet)
- ✅ Automated test proves the not-found path triggers correctly (`test_not_found_returns_empty_sources`, `test_not_found_substring_triggers_false`, `test_grounded_path_with_fake_embeddings_and_fake_llm`)
- ✅ Streamlit UI works end to end, and swapping document sets works cleanly (Clear Session → new files → rebuild)
- ✅ pytest passes fully offline (16 tests, `FakeEmbeddings`, `FakeListChatModel`)
- ✅ README covers setup and running it
- ✅ `transcripts/` is ready for session export

---

## Scope Notes (Deliberate 45-Minute Decisions)

The following are **explicitly out of scope** for this build:

- ❌ **LangGraph** — no multi-step agents or state machines
- ❌ **Hybrid/BM25 search** — pure vector similarity only
- ❌ **Reranking** — no cross-encoder or LLM-based reranking
- ❌ **Streaming tokens** — single `.invoke()`, no token-by-token output
- ❌ **Conversation memory** — stateless Q&A, no chat history in context
- ❌ **Guardrail modules** — no PII detection, toxicity filters, etc.
- ❌ **Docker** — no containerization
- ❌ **Eval harness** — no automated quality benchmarks
- ❌ **DOCX support** — only PDF, TXT, MD

These omissions are intentional for the 45-minute timebox. A production version would address them incrementally.

---

## License

MIT