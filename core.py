from __future__ import annotations

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from io import BytesIO

from langchain_core.documents import Document
from langchain_core.runnables import RunnableParallel, RunnablePassthrough, RunnableLambda
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama
from pypdf import PdfReader


NOT_FOUND_SENTINEL = "I don't have enough information in the provided documents to answer that."

SYSTEM_PROMPT = """You are a helpful assistant that answers questions using only the provided context.

The context consists of numbered blocks. Each block shows its source and page number.

Rules:
- Answer ONLY using information from the context blocks.
- Cite your sources using square brackets with the block number, e.g., [1], [2].
- If the context does not contain enough information to answer the question, output exactly this sentence and nothing else: "{sentinel}"

Context:
{{context}}

Question: {{question}}

Answer:""".format(sentinel=NOT_FOUND_SENTINEL)

PROMPT_TEMPLATE = ChatPromptTemplate.from_template(SYSTEM_PROMPT)


@dataclass
class AnswerResult:
    answer: str
    is_grounded: bool
    sources: List[Dict[str, Any]]


def load_document(file_bytes: bytes, filename: str) -> List[Document]:
    docs = []
    ext = filename.lower().split(".")[-1]

    if ext == "pdf":
        reader = PdfReader(BytesIO(file_bytes))
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={"source": filename, "page": i + 1}
                ))
    elif ext in ("txt", "md"):
        text = file_bytes.decode("utf-8")
        if text.strip():
            docs.append(Document(
                page_content=text,
                metadata={"source": filename, "page": None}
            ))
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    return docs


def chunk_documents(
    docs: List[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    return chunks


def get_embeddings(
    model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
) -> OllamaEmbeddings:
    return OllamaEmbeddings(model=model, base_url=base_url)


def build_index(chunks: List[Document], embeddings: OllamaEmbeddings) -> FAISS:
    return FAISS.from_documents(chunks, embeddings)


def get_llm(
    model: str = "llama3.2",
    base_url: str = "http://localhost:11434",
) -> ChatOllama:
    return ChatOllama(model=model, base_url=base_url, temperature=0)


def format_docs(docs: List[Document]) -> str:
    lines = []
    for i, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page")
        page_str = f", page {page}" if page is not None else ""
        lines.append(f"[{i}] Source: {source}{page_str}\n{doc.page_content}")
    return "\n\n".join(lines)


def build_rag_chain(retriever, llm):
    chain = (
        RunnableParallel(docs=retriever, question=RunnablePassthrough())
        .assign(
            answer=(
                RunnableLambda(lambda x: {"context": format_docs(x["docs"]), "question": x["question"]})
                | PROMPT_TEMPLATE
                | llm
                | StrOutputParser()
            )
        )
    )
    return chain


def ask(chain, question: str) -> AnswerResult:
    result = chain.invoke(question)
    answer = result["answer"].strip()
    docs = result["docs"]

    is_grounded = NOT_FOUND_SENTINEL not in answer

    sources = []
    if is_grounded:
        for doc in docs:
            sources.append({
                "source": doc.metadata.get("source", "unknown"),
                "page": doc.metadata.get("page"),
                "snippet": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content,
            })

    return AnswerResult(answer=answer, is_grounded=is_grounded, sources=sources)