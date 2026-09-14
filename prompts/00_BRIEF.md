# RAG Generator build brief

I need a RAG Generator built to spec below. This message just sets the ground rules — don't write any code yet, wait for the next message.

## What it needs to do

Documents get uploaded at runtime, no code changes needed to point it at a new set. It builds a RAG app over whatever's uploaded. Users ask questions and get answers grounded in the documents, with the system saying "not found" explicitly when it doesn't know rather than guessing.

## Time budget

I'll feed you three follow-up prompts after this one:

1. `01_core_pipeline.md`
2. `02_streamlit_ui.md`
3. `03_tests_and_readme.md`

I will do my own smoke test at the end. Keep pace with that — if something's dragging, simplify rather than debug forever.

## Stack

Python 3.10+, LangChain with LCEL, FAISS as the vector store (`langchain_community.vectorstores.FAISS`), Ollama for both embeddings and generation (`nomic-embed-text` and `llama3.2` via `langchain-ollama`), Streamlit for the UI. Tests run on pytest using fakes — I don't want the test suite depending on Ollama actually running.

## What NOT to build

No LangGraph, no hybrid/BM25 search, no reranking, no streaming tokens, no conversation memory, no guardrail modules, no Docker, no eval harness, no DOCX support. If you catch yourself reaching for any of these, stop — none of it belongs in this pass. (There's a bigger version of this scoped separately, this isn't that.)

## Repo layout — keep it to two Python files
Rag-Generator/
├── prompts
│ └── #all the prompts
├── core.py # everything: loading, chunking, embeddings, FAISS,
│ # the LCEL chain, not-found detection, citations —
│ # importable, no UI code in here
├── app.py # Streamlit UI, just calls into core.py
├── requirements.txt
├── tests/
│ └── test_core.py # offline tests, fakes only
├── sample_docs/
│ ├── company_handbook.txt
│ └── product_faq.txt
├── transcripts/
│ └── README.md
├── .gitignore
└── README.md


## Rules I actually care about

`core.py` shouldn't import Streamlit at all — `app.py` should only ever call functions on `core`. Keep them properly separated.

Every time someone hits "build index," it should throw away whatever was there and build a fresh FAISS index from what's currently uploaded. That's the whole trick to swapping document sets without touching code — don't overcomplicate it with merging or persistence across sessions.

The LCEL chain needs to hand back the generated answer AND the documents it actually retrieved from a single `.invoke()` — use `RunnableParallel` plus `.assign(...)` for this. I don't want two disconnected calls where the citations aren't provably tied to what was retrieved.

For "not found," pick one exact sentence (something like "I don't have enough information in the provided documents to answer that.") and have the system prompt instruct the model to output it verbatim when the context doesn't answer the question. Then check for that literal string in code to flag `is_grounded=False`. This needs an actual test proving it fires — I'm not going to just trust the prompt.

Citations need to come back as structured data — filename, page if there is one, a text snippet — not just mentioned somewhere in the prose.

Commit after each stage with a real message, and run pytest before every commit.

## How I'll know it's done

- Upload a PDF or TXT at runtime, build the index, no code edits required
- Chunking works and is configurable
- FAISS retrieval actually returns relevant chunks
- The LCEL chain gives a grounded answer with citations
- There's an automated test that proves the not-found path triggers correctly
- The Streamlit UI works end to end, and swapping document sets works cleanly
- pytest passes fully offline
- README covers setup and running it
- `transcripts/` is ready for me to drop the session export into

Go ahead and set up, then wait — I'll send `01_core_pipeline.md` next.