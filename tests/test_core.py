import pytest
from unittest.mock import Mock, patch
from typing import List

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_community.vectorstores import FAISS

from core import (
    load_document,
    chunk_documents,
    get_embeddings,
    build_index,
    get_llm,
    format_docs,
    build_rag_chain,
    ask,
    AnswerResult,
    NOT_FOUND_SENTINEL,
)


class FakeEmbeddings(Embeddings):
    """Deterministic hash-based embeddings for offline testing."""
    
    def __init__(self, dimension: int = 32):
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

    def _embed(self, text: str) -> List[float]:
        h = hash(text)
        return [float((h >> (i * 8)) & 0xFF) / 255.0 for i in range(self.dimension)]


class TestLoadDocument:
    def test_load_txt_bytes(self):
        content = b"Hello world\nThis is a test."
        docs = load_document(content, "test.txt")
        assert len(docs) == 1
        assert docs[0].page_content == "Hello world\nThis is a test."
        assert docs[0].metadata["source"] == "test.txt"
        assert docs[0].metadata["page"] is None

    def test_load_md_bytes(self):
        content = b"# Header\n\nContent here."
        docs = load_document(content, "test.md")
        assert len(docs) == 1
        assert docs[0].page_content == "# Header\n\nContent here."

    def test_load_pdf_bytes(self):
        content = b"%PDF-1.4 dummy"
        with patch("core.PdfReader") as mock_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = "Page 1 content"
            mock_reader.return_value.pages = [mock_page]
            docs = load_document(content, "test.pdf")
            assert len(docs) == 1
            assert docs[0].page_content == "Page 1 content"
            assert docs[0].metadata["source"] == "test.pdf"
            assert docs[0].metadata["page"] == 1

    def test_load_pdf_multiple_pages(self):
        content = b"%PDF-1.4 dummy"
        with patch("core.PdfReader") as mock_reader:
            mock_page1 = Mock()
            mock_page1.extract_text.return_value = "Page 1"
            mock_page2 = Mock()
            mock_page2.extract_text.return_value = "Page 2"
            mock_reader.return_value.pages = [mock_page1, mock_page2]
            docs = load_document(content, "test.pdf")
            assert len(docs) == 2
            assert docs[0].metadata["page"] == 1
            assert docs[1].metadata["page"] == 2

    def test_load_empty_returns_empty_list(self):
        docs = load_document(b"   \n\n  ", "empty.txt")
        assert docs == []

    def test_load_unsupported_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            load_document(b"data", "test.docx")


class TestChunkDocuments:
    def test_long_text_produces_multiple_chunks_with_chunk_id(self):
        docs = [Document(page_content="A" * 2000, metadata={"source": "test.txt", "page": 1})]
        chunks = chunk_documents(docs)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.page_content) <= 800
            assert "chunk_id" in chunk.metadata

    def test_short_text_produces_one_chunk(self):
        docs = [Document(page_content="Short text.", metadata={"source": "test.txt", "page": 1})]
        chunks = chunk_documents(docs)
        assert len(chunks) == 1
        assert chunks[0].metadata["chunk_id"] == 0


class TestBuildIndexAndRetrieval:
    def test_build_index_and_retrieve_returns_documents(self):
        embeddings = FakeEmbeddings(dimension=32)
        docs = [
            Document(page_content="AcmeWidget Pro pricing: Professional tier $29/user/month.", metadata={"source": "faq.txt", "page": 1}),
            Document(page_content="Company handbook: work hours 9am-5pm, core hours 10am-3pm.", metadata={"source": "handbook.txt", "page": 2}),
            Document(page_content="Health benefits: medical, dental, vision. Company pays 80%.", metadata={"source": "handbook.txt", "page": 3}),
        ]
        vectorstore = build_index(docs, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        results = retriever.invoke("pricing")
        
        assert len(results) == 2
        for r in results:
            assert isinstance(r, Document)
            assert "source" in r.metadata


class TestFormatDocs:
    def test_formats_docs_with_numbers_and_metadata(self):
        docs = [
            Document(page_content="Content one", metadata={"source": "a.txt", "page": 1}),
            Document(page_content="Content two", metadata={"source": "b.txt", "page": None}),
        ]
        result = format_docs(docs)
        assert "[1] Source: a.txt, page 1" in result
        assert "Content one" in result
        assert "[2] Source: b.txt" in result
        assert "Content two" in result


class TestBuildRagChain:
    def test_creates_chain_with_runnable_parallel(self):
        mock_retriever = Mock()
        mock_llm = Mock()

        chain = build_rag_chain(mock_retriever, mock_llm)

        assert chain is not None
        assert hasattr(chain, "invoke")


class TestAsk:
    def test_grounded_answer_returns_sources(self):
        mock_docs = [
            Document(page_content="Source content about pricing.", metadata={"source": "doc1.txt", "page": 5}),
        ]
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "docs": mock_docs,
            "question": "Test question",
            "answer": "The price is $29. [1]",
        }

        result = ask(mock_chain, "Test question")

        assert isinstance(result, AnswerResult)
        assert result.answer == "The price is $29. [1]"
        assert result.is_grounded is True
        assert len(result.sources) == 1
        assert result.sources[0]["source"] == "doc1.txt"
        assert result.sources[0]["page"] == 5

    def test_not_found_returns_empty_sources(self):
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "docs": [],
            "question": "Unknown question",
            "answer": NOT_FOUND_SENTINEL,
        }

        result = ask(mock_chain, "Unknown question")

        assert result.answer == NOT_FOUND_SENTINEL
        assert result.is_grounded is False
        assert result.sources == []

    def test_not_found_substring_triggers_false(self):
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "docs": [],
            "question": "Unknown question",
            "answer": f"Sorry, {NOT_FOUND_SENTINEL}",
        }

        result = ask(mock_chain, "Unknown question")

        assert result.is_grounded is False
        assert result.sources == []

    def test_grounded_path_with_fake_embeddings_and_fake_llm(self):
        """Integration test: full pipeline with FakeEmbeddings and FakeListChatModel."""
        embeddings = FakeEmbeddings(dimension=32)
        docs = [
            Document(page_content="AcmeWidget Pro Professional tier costs $29/user/month.", metadata={"source": "faq.txt", "page": 1}),
            Document(page_content="Starter tier is $12/user/month.", metadata={"source": "faq.txt", "page": 1}),
        ]
        vectorstore = build_index(docs, embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        fake_llm = FakeListChatModel(responses=["Professional tier costs $29/user/month. [1]"])
        chain = build_rag_chain(retriever, fake_llm)

        result = ask(chain, "How much is Professional tier?")

        assert result.is_grounded is True
        assert len(result.sources) > 0
        assert result.sources[0]["source"] == "faq.txt"


class TestNotFoundSentinel:
    def test_sentinel_is_expected_string(self):
        assert NOT_FOUND_SENTINEL == "I don't have enough information in the provided documents to answer that."