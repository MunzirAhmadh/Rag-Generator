from __future__ import annotations

import os
import tempfile
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama
from pypdf import PdfReader


NOT_FOUND_MESSAGE = "I don't have enough information in the provided documents to answer that."


@dataclass
class Citation:
    filename: str
    page: Optional[int]
    snippet: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "page": self.page,
            "snippet": self.snippet,
        }


@dataclass
class RAGResult:
    answer: str
    citations: List[Citation]
    is_grounded: bool


def load_documents(file_paths: List[str]) -> List[Document]:
    docs = []
    for path in file_paths:
        filename = os.path.basename(path)
        if path.lower().endswith(".pdf"):
            reader = PdfReader(path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={"source": filename, "page": i + 1}
                    ))
        elif path.lower().endswith(".txt"):
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": filename, "page": None}
                ))
    return docs


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def build_faiss_index(
    documents: List[Document],
    embedding_model: str = "nomic-embed-text",
) -> FAISS:
    embeddings = OllamaEmbeddings(model=embedding_model)
    return FAISS.from_documents(documents, embeddings)


def create_rag_chain(vectorstore: FAISS, generation_model: str = "llama3.2"):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    prompt = ChatPromptTemplate.from_template(
        f"""You are a helpful assistant that answers questions using only the provided context.
If the context does not contain enough information to answer the question, you must output exactly: "{NOT_FOUND_MESSAGE}"
Do not add any extra text, explanation, or apology when the answer is not found.

Context:
{{context}}

Question: {{question}}

Answer:"""
    )

    llm = ChatOllama(model=generation_model, temperature=0)

    def format_docs(docs: List[Document]) -> str:
        return "\n\n".join(
            f"[Source: {d.metadata.get('source', 'unknown')}, Page: {d.metadata.get('page', 'N/A')}]\n{d.page_content}"
            for d in docs
        )

    def extract_citations(docs: List[Document]) -> List[Citation]:
        citations = []
        for d in docs:
            snippet = d.page_content[:200] + "..." if len(d.page_content) > 200 else d.page_content
            citations.append(Citation(
                filename=d.metadata.get("source", "unknown"),
                page=d.metadata.get("page"),
                snippet=snippet,
            ))
        return citations

    chain = (
        RunnableParallel({
            "context": retriever | RunnableLambda(format_docs),
            "question": RunnablePassthrough(),
            "retrieved_docs": retriever,
        })
        .assign(
            answer=lambda x: prompt.invoke({"context": x["context"], "question": x["question"]}) | llm | StrOutputParser(),
            citations=lambda x: extract_citations(x["retrieved_docs"]),
        )
    )

    return chain


def run_rag_query(
    chain,
    question: str,
) -> RAGResult:
    result = chain.invoke(question)
    answer = result["answer"].strip()
    citations = result["citations"]
    is_grounded = NOT_FOUND_MESSAGE not in answer
    return RAGResult(answer=answer, citations=citations, is_grounded=is_grounded)


class RAGPipeline:
    def __init__(
        self,
        embedding_model: str = "nomic-embed-text",
        generation_model: str = "llama3.2",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.embedding_model = embedding_model
        self.generation_model = generation_model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.vectorstore: Optional[FAISS] = None
        self.chain = None

    def build_index(self, file_paths: List[str]) -> None:
        documents = load_documents(file_paths)
        chunks = chunk_documents(documents, self.chunk_size, self.chunk_overlap)
        self.vectorstore = build_faiss_index(chunks, self.embedding_model)
        self.chain = create_rag_chain(self.vectorstore, self.generation_model)

    def query(self, question: str) -> RAGResult:
        if self.chain is None:
            raise RuntimeError("Index not built. Call build_index() first.")
        return run_rag_query(self.chain, question)

    def is_ready(self) -> bool:
        return self.chain is not None