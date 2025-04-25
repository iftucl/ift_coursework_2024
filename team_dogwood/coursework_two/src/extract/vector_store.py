#!/usr/bin/env python3
"""
vector_store.py
===============

A tiny CLI utility that:

* **build** – converts Markdown/​text files into a persisted vector index
  (HuggingFace sentence-transformer embeddings, stored on disk).
* **query** – performs similarity retrieval **plus** answer synthesis with GPT-4,
  printing the answer and the supporting context.

Designed to be a minimal, self-contained example of a
`Retrieval-Augmented Generation (RAG)`_ workflow.

.. _Retrieval-Augmented Generation (RAG): https://www.pinecone.io/learn/retrieval-augmented-generation/
"""

# ── standard library ──────────────────────────────────────────────────────
import argparse
import os
from pathlib import Path
from textwrap import indent, shorten

# ── third-party ────────────────────────────────────────────────────────────
from loguru import logger
from llama_index.core import (
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.openai import OpenAI


# ────────────────────────── builders & queries ────────────────────────────
def build_index(input_dir: Path, persist_dir: Path, model_name: str) -> None:
    """
    Build a local vector store from all files inside *input_dir* and persist
    it to *persist_dir*.

    Parameters
    ----------
    input_dir : :class:`pathlib.Path`
        Folder that contains Markdown or plain-text files.
    persist_dir : :class:`pathlib.Path`
        Destination directory for the on-disk index.
    model_name : str
        HuggingFace sentence-transformer model (e.g. ``"all-MiniLM-L6-v2"``).

    Raises
    ------
    FileNotFoundError
        If *input_dir* does not exist or is empty.
    """
    if not input_dir.is_dir():
        raise FileNotFoundError(f"{input_dir} missing")
    if not any(input_dir.iterdir()):
        raise FileNotFoundError(f"{input_dir} is empty")

    docs = SimpleDirectoryReader(str(input_dir)).load_data()
    logger.info("Loaded %d docs", len(docs))

    embed_model = HuggingFaceEmbedding(model_name=model_name)

    index = VectorStoreIndex.from_documents(
        docs,
        embed_model=embed_model,
        storage_context=StorageContext.from_defaults(),
    )

    persist_dir.mkdir(parents=True, exist_ok=True)
    index.storage_context.persist(persist_dir=str(persist_dir))
    logger.success("Index saved → %s", persist_dir)


def query_index(
    query_text: str,
    persist_dir: Path,
    model_name: str,
    top_k: int,
    openai_model: str,
    openai_key: str | None,
) -> None:
    """
    Retrieve *top_k* most-similar chunks and let GPT-4 synthesize an answer.

    Parameters
    ----------
    query_text : str
        Natural-language question.
    persist_dir : :class:`pathlib.Path`
        Folder that contains a previously-built vector index.
    model_name : str
        HuggingFace embedding model used for the query vector.
    top_k : int
        Number of nearest neighbors to retrieve.
    openai_model : str
        e.g. ``"gpt-4o-mini"`` – the LLM used for answer synthesis.
    openai_key : str | None
        OpenAI API key.  If *None*, an :class:`EnvironmentError`
        is raised **before** this function is called.

    Raises
    ------
    FileNotFoundError
        If *persist_dir* is missing.
    """
    if not persist_dir.is_dir():
        raise FileNotFoundError(f"{persist_dir} missing")

    # 1 ⎯ reload index
    embed_model = HuggingFaceEmbedding(model_name=model_name)
    storage_ctx = StorageContext.from_defaults(persist_dir=str(persist_dir))
    index = load_index_from_storage(storage_ctx, embed_model=embed_model)

    # 2 ⎯ GPT-4
    llm = OpenAI(model=openai_model, api_key=openai_key)

    # 3 ⎯ query + synthesis
    query_engine = index.as_query_engine(similarity_top_k=top_k, llm=llm)
    answer = query_engine.query(query_text)

    # 4 ⎯ pretty-print
    logger.success("Answer ↓\n")
    print(indent(str(answer), "  "))

    logger.info("\nSources ↓")
    for i, node in enumerate(answer.source_nodes, 1):
        snippet = shorten(node.node.text.replace("\n", " "),
                          width=400, placeholder=" …")
        print(f"{i}. {snippet}\n")


# ─────────────────────────────── CLI helpers ──────────────────────────────
def parse_args() -> argparse.Namespace:
    """
    Build the :pyclass:`argparse.Namespace` for the *build* / *query* sub-CLI.

    Returns
    -------
    argparse.Namespace
        Parsed command-line arguments.
    """
    p = argparse.ArgumentParser(
        description="Build **or** query a GPT-4-powered vector store"
    )
    sp = p.add_subparsers(dest="cmd", required=True)

    # build
    b = sp.add_parser("build", help="Create the vector index")
    b.add_argument("-i", "--input_dir", type=Path, required=True)
    b.add_argument("-p", "--persist_dir", type=Path,
                   default=Path("data/vector_db"))
    b.add_argument("-m", "--model_name", default="all-MiniLM-L6-v2")

    # query
    q = sp.add_parser("query", help="Ask a question")
    q.add_argument("query")
    q.add_argument("-p", "--persist_dir", type=Path,
                   default=Path("data/vector_db"))
    q.add_argument("-m", "--model_name", default="all-MiniLM-L6-v2")
    q.add_argument("-k", "--top_k", type=int, default=5)
    q.add_argument("--openai_model", default="gpt-4o-mini")
    q.add_argument("--openai_key", default=os.getenv("OPENAI_API_KEY"))
    return p.parse_args()


def main() -> None:
    """
    Entrypoint for ``python vector_store.py …``.
    Dispatches to :func:`build_index` or :func:`query_index` based on *cmd*.
    """
    args = parse_args()
    if args.cmd == "build":
        build_index(args.input_dir, args.persist_dir, args.model_name)
    else:  # query
        if not args.openai_key:
            raise EnvironmentError(
                "OPENAI_API_KEY not set. Export it or pass --openai_key."
            )
        query_index(
            args.query,
            args.persist_dir,
            args.model_name,
            args.top_k,
            args.openai_model,
            args.openai_key,
        )


if __name__ == "__main__":  # pragma: no cover
    main()
