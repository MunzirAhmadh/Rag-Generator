# STAGE 3 — Tests, sample docs, README

Context: `core.py` and `app.py` are committed and working. This is the
final stage — it's what makes the submission credible, don't rush it
more than the earlier stages.

## Task

1. `tests/test_core.py` — fully offline, no live Ollama required:
   - A `FakeEmbeddings` class (deterministic, e.g. hash-based fixed-size
     vectors) implementing `langchain_core.embeddings.Embeddings`.
   - Test `load_document`: normal `.txt`, empty `.txt` → `[]`,
     unsupported extension → raises.
   - Test `chunk_documents`: long text produces multiple chunks with
     `chunk_id` in metadata; short text produces one chunk.
   - Test `build_index` + retrieval: build from 2-3 fake `Document`s,
     retrieve, confirm it returns real `Document` objects (don't assert
     exact semantic ranking since embeddings are fake/hashed).
   - Test `ask()` grounded path: `FakeListChatModel` returns a canned
     answer with citation marker → `is_grounded=True`, `sources`
     populated with correct `source` field.
   - Test `ask()` not-found path: `FakeListChatModel` returns
     `core.NOT_FOUND_SENTINEL` → `is_grounded=False`, `sources=[]`.
   - Test `format_docs`: numbered output includes source names.
   - Aim for 8-10 tests total, each asserting one specific behavior.

2. `sample_docs/company_handbook.txt` and `sample_docs/product_faq.txt`
   — two short (10-20 line) realistic documents on different topics, so
   a grader can demonstrate the "different document sets, no code
   changes" requirement by swapping between them.

3. `requirements.txt`: `streamlit`, `langchain-core`, `langchain-community`,
   `langchain-text-splitters`, `langchain-ollama`, `faiss-cpu`, `pypdf`,
   `numpy`, `pytest`.

4. `.gitignore`: venv, `__pycache__`, `.env`, `.pytest_cache`.

5. `README.md` covering:
   - What this is, one paragraph.
   - Architecture: a short diagram (upload → load → chunk → embed → FAISS;
     question → retrieve → LCEL chain → grounded answer + citations).
   - Prerequisites: Python, Ollama + which models to pull.
   - Setup + run commands (venv, pip install, `ollama serve`,
     `streamlit run app.py`).
   - `pytest tests/ -v` — note it runs fully offline.
   - Usage walkthrough using the two sample docs, including one example
     question per doc set and one deliberately off-topic question to
     demonstrate the not-found path.
   - A must-have checklist from the assessment brief, checked off.
   - A short "scope notes" section: explicitly list what's out of scope
     for this pass (LangGraph, hybrid search, reranking, streaming,
     memory, guardrails, Docker, eval harness, DOCX) so it reads as a
     deliberate 45-minute-scoped decision, not a missed requirement.

6. `transcripts/README.md`: instructs exporting the opencode session
   transcript into this folder before submission.

## Acceptance criteria

- `pytest tests/ -v` passes, all offline, zero live network calls.
- `README.md` alone would let someone with no context clone, set up, and
  run the app.
- Re-check the Definition of Done checklist from `00_BRIEF.md` item by
  item and report the result.

Final commit: "Add tests, sample docs, and README". This completes the
45-minute build. Export the opencode transcript into `transcripts/`
before submitting.
