import pytest
from unittest.mock import Mock, MagicMock, patch
from core import (
    load_documents,
    chunk_documents,
    build_faiss_index,
    create_rag_chain,
    run_rag_query,
    RAGPipeline,
    RAGResult,
    Citation,
    NOT_FOUND_MESSAGE,
)


class TestLoadDocuments:
    def test_load_txt_file(self, tmp_path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world\nThis is a test.")
        docs = load_documents([str(txt_file)])
        assert len(docs) == 1
        assert docs[0].page_content == "Hello world\nThis is a test."
        assert docs[0].metadata["source"] == "test.txt"
        assert docs[0].metadata["page"] is None

    def test_load_pdf_file(self, tmp_path):
        pdf_file = tmp_path / "test.pdf"
        with open(pdf_file, "wb") as f:
            f.write(b"%PDF-1.4\n%Dummy PDF content")
        with patch("core.PdfReader") as mock_reader:
            mock_page = Mock()
            mock_page.extract_text.return_value = "Page 1 content"
            mock_reader.return_value.pages = [mock_page]
            docs = load_documents([str(pdf_file)])
            assert len(docs) == 1
            assert docs[0].page_content == "Page 1 content"
            assert docs[0].metadata["source"] == "test.pdf"
            assert docs[0].metadata["page"] == 1


class TestChunkDocuments:
    def test_chunks_documents(self):
        docs = [Mock(page_content="A" * 1500, metadata={"source": "test.txt", "page": 1})]
        chunks = chunk_documents(docs, chunk_size=500, chunk_overlap=100)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk.page_content) <= 500


class TestBuildFaissIndex:
    @patch("core.OllamaEmbeddings")
    @patch("core.FAISS")
    def test_builds_index(self, mock_faiss, mock_embeddings):
        mock_embeddings_instance = Mock()
        mock_embeddings.return_value = mock_embeddings_instance
        mock_vectorstore = Mock()
        mock_faiss.from_documents.return_value = mock_vectorstore

        docs = [Mock(page_content="test", metadata={})]
        result = build_faiss_index(docs, "test-model")

        mock_embeddings.assert_called_once_with(model="test-model")
        mock_faiss.from_documents.assert_called_once_with(docs, mock_embeddings_instance)
        assert result == mock_vectorstore


class TestCreateRagChain:
    def test_creates_chain_with_retriever(self):
        mock_vectorstore = Mock()
        mock_retriever = Mock()
        mock_vectorstore.as_retriever.return_value = mock_retriever

        chain = create_rag_chain(mock_vectorstore, "test-model")

        mock_vectorstore.as_retriever.assert_called_once_with(search_kwargs={"k": 4})
        assert chain is not None


class TestRunRagQuery:
    def test_returns_grounded_result(self):
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "answer": "The answer is 42.",
            "citations": [
                Citation(filename="doc1.txt", page=1, snippet="The answer is 42..."),
            ],
        }

        result = run_rag_query(mock_chain, "What is the answer?")

        assert isinstance(result, RAGResult)
        assert result.answer == "The answer is 42."
        assert result.is_grounded is True
        assert len(result.citations) == 1

    def test_returns_not_found_result(self):
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "answer": NOT_FOUND_MESSAGE,
            "citations": [],
        }

        result = run_rag_query(mock_chain, "Unknown question")

        assert result.answer == NOT_FOUND_MESSAGE
        assert result.is_grounded is False
        assert result.citations == []

    def test_not_found_with_extra_whitespace(self):
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "answer": f"  {NOT_FOUND_MESSAGE}  ",
            "citations": [],
        }

        result = run_rag_query(mock_chain, "Unknown question")

        assert result.is_grounded is False


class TestRAGPipeline:
    @patch("core.build_faiss_index")
    @patch("core.chunk_documents")
    @patch("core.load_documents")
    def test_build_index(self, mock_load, mock_chunk, mock_build):
        mock_load.return_value = [Mock()]
        mock_chunk.return_value = [Mock()]
        mock_vectorstore = Mock()
        mock_build.return_value = mock_vectorstore

        pipeline = RAGPipeline()
        pipeline.build_index(["doc1.txt", "doc2.pdf"])

        mock_load.assert_called_once_with(["doc1.txt", "doc2.pdf"])
        mock_chunk.assert_called_once()
        mock_build.assert_called_once()
        assert pipeline.vectorstore == mock_vectorstore
        assert pipeline.chain is not None

    @patch("core.run_rag_query")
    def test_query(self, mock_run):
        mock_result = RAGResult(answer="Test answer", citations=[], is_grounded=True)
        mock_run.return_value = mock_result

        pipeline = RAGPipeline()
        pipeline.chain = Mock()

        result = pipeline.query("Test question")

        assert result == mock_result
        mock_run.assert_called_once_with(pipeline.chain, "Test question")

    def test_query_without_index_raises(self):
        pipeline = RAGPipeline()
        with pytest.raises(RuntimeError, match="Index not built"):
            pipeline.query("Test question")

    def test_is_ready(self):
        pipeline = RAGPipeline()
        assert pipeline.is_ready() is False
        pipeline.chain = Mock()
        assert pipeline.is_ready() is True


class TestCitation:
    def test_to_dict(self):
        cit = Citation(filename="test.txt", page=5, snippet="Hello world")
        d = cit.to_dict()
        assert d == {"filename": "test.txt", "page": 5, "snippet": "Hello world"}

    def test_to_dict_no_page(self):
        cit = Citation(filename="test.txt", page=None, snippet="Hello")
        d = cit.to_dict()
        assert d == {"filename": "test.txt", "page": None, "snippet": "Hello"}


class TestNotFoundDetection:
    def test_exact_not_found_message_triggers_false(self):
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "answer": NOT_FOUND_MESSAGE,
            "citations": [],
        }
        result = run_rag_query(mock_chain, "test")
        assert result.is_grounded is False

    def test_answer_containing_not_found_as_substring(self):
        mock_chain = Mock()
        mock_chain.invoke.return_value = {
            "answer": f"Based on the documents, {NOT_FOUND_MESSAGE}",
            "citations": [],
        }
        result = run_rag_query(mock_chain, "test")
        assert result.is_grounded is False