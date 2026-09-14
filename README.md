# RAG Generator

A Retrieval-Augmented Generation application built with LangChain, FAISS, Ollama, and Streamlit.

## Features

- Upload PDF/TXT documents at runtime
- Build FAISS vector index on-demand
- Grounded answers with structured citations
- Explicit "not found" detection
- Fully offline testable with pytest

## Requirements

- Python 3.10+
- Ollama running locally with models:
  - `nomic-embed-text` (embeddings)
  - `llama3.2` (generation)

## Installation

```bash
# Clone and navigate
cd Rag-Generator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Pull Ollama models
ollama pull nomic-embed-text
ollama pull llama3.2
```

## Running

### Start Ollama (in separate terminal)
```bash
ollama serve
```

### Run the Streamlit App
```bash
streamlit run app.py
```

Open http://localhost:8501 in your browser.

### Run Tests (offline, no Ollama needed)
```bash
pytest tests/ -v
```

## Usage

1. **Configure models** in the sidebar (defaults work with standard Ollama setup)
2. **Upload documents** - PDF or TXT files, multiple at once
3. **Click "Build Index"** - creates fresh FAISS index from uploaded files
4. **Ask questions** - answers include citations with filename, page, and text snippet
5. **Swap documents** - upload new files and click "Build Index" again to replace

## Architecture

```
Rag-Generator/
├── core.py          # All RAG logic: loading, chunking, embeddings, FAISS, LCEL chain
├── app.py           # Streamlit UI only, calls into core.py
├── requirements.txt
├── tests/
│   └── test_core.py # Offline tests using mocks/fakes
├── sample_docs/     # Example documents for testing
└── transcripts/     # Session exports
```

### Key Design Decisions

- **core.py** has zero Streamlit imports - fully importable and testable
- **Fresh index on each build** - no persistence, enables document swapping
- **LCEL with RunnableParallel** - single `.invoke()` returns answer + retrieved docs
- **Exact not-found string** - model instructed to output verbatim sentence, checked in code
- **Structured citations** - filename, page, snippet as dataclass, not embedded in prose

## Configuration

Adjust in sidebar:
- Embedding model (default: `nomic-embed-text`)
- Generation model (default: `llama3.2`)
- Chunk size (default: 1000)
- Chunk overlap (default: 200)

## Testing

Tests use `unittest.mock` to fake Ollama, FAISS, and PDF loading. No network or model required.

```bash
pytest tests/test_core.py -v
```

## License

MIT