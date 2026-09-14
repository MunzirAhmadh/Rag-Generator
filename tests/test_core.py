import pytest
from unittest.mock import Mock, MagicMock, patch
from io import BytesIO

from langchain_core.documents import Document
from langchain_core.language_models.fake_chat_models import FakeListChatModel

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
    def test_chunks_with_defaults(self):
        docs = [Document(page_content="A" * 2000, metadata={"source": "test.txt", "page": 1})]
        chunks = chunk_documents(docs)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.page_content) <= 800
            assert "chunk_id" in chunk.metadata

    def test_chunks_custom_size(self):
        docs = [Document(page_content="A" * 1000, metadata={"source": "test.txt", "page": 1})]
        chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=50)
        assert len(chunks) >= 4
        for chunk in chunks:
            assert len(chunk.page_content) <= 200


class TestGetEmbeddings:
    @patch("core.OllamaEmbeddings")
    def test_returns_embeddings_with_defaults(self, mock_embeddings):
        mock_instance = Mock()
        mock_embeddings.return_value = mock_instance

        result = get_embeddings()

        mock_embeddings.assert_called_once_with(model="nomic-embed-text", base_url="http://localhost:11434")
        assert result == mock_instance

    @patch("core.OllamaEmbeddings")
    def test_returns_embeddings_with_custom_params(self, mock_embeddings):
        mock_instance = Mock()
        mock_embeddings.return_value = mock_instance

        result = get_embeddings(model="custom-embed", base_url="http://custom:11434")

        mock_embeddings.assert_called_once_with(model="custom-embed", base_url="http://custom:11434")
        assert result == mock_instance


class TestBuildIndex:
    @patch("core.FAISS")
    def test_builds_fresh_index(self, mock_faiss):
        mock_vectorstore = Mock()
        mock_faiss.from_documents.return_value = mock_vectorstore
        mock_embeddings = Mock()

        chunks = [Mock(), Mock()]
        result = build_index(chunks, mock_embeddings)

        mock_faiss.from_documents.assert_called_once_with(chunks, mock_embeddings)
        assert result == mock_vectorstore


class TestGetLLM:
    @patch("core.ChatOllama")
    def test_returns_llm_with_defaults(self, mock_llm):
        mock_instance = Mock()
        mock_llm.return_value = mock_instance

        result = get_llm()

        mock_llm.assert_called_once_with(model="llama3.2", base_url="http://localhost:11434", temperature=0)
        assert result == mock_instance


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
        # Chain should have invoke method
        assert hasattr(chain, "invoke")


class TestAsk:
    def test_grounded_answer_returns_sources(self):
        mock_retriever = Mock()
        mock_llm = FakeListChatModel(responses=["Answer is here. [1]"])

        chain = build_rag_chain(mock_retriever, mock_llm)

        # Mock retriever to return docs
        mock_docs = [
            Document(page_content="Source content", metadata={"source": "doc1.txt", "page": 5}),
        ]
        mock_retriever.invoke = Mock(return_value=mock_docs)

        # The chain's parallel step calls retriever, need to mock the full chain invoke
        # Instead, test ask by directly calling with a mock chain that returns expected structure
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "docs": mock_docs,
            "question": "Test question",
            "answer": "Answer is here. [1]",
        }

        result = ask(mock_chain, "Test question")

        assert isinstance(result, AnswerResult)
        assert result.answer == "Answer is here. [1]"
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


class TestNotFoundSentinel:
    def test_sentinel_is_expected_string(self):
        assert NOT_FOUND_SENTINEL == "I don't have enough information in the provided documents to answer that."