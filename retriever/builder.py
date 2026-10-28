from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

from config.settings import settings
from retriever.embeddings import get_embedding

import hashlib
import json
import logging


logger = logging.getLogger(__name__)


class RetrieverBuilder:
    def __init__(self):
        """Initialize the retriever with a cached, local multilingual model."""
        self.embeddings = get_embedding()
        logger.info("Local embeddings initialized: %s", settings.EMBEDDING_MODEL)

    def build_hybrid_retriever(self, docs):
        """
        Build a hybrid retriever using BM25 and vector-based retrieval.
        """
        try:
            if not docs:
                raise ValueError("No document fragments were produced for indexing")
            # Bind each retriever to exactly its active corpus. The legacy shared
            # collection accumulates uploads and must never be queried here.
            documents_by_id = {}
            for doc in docs:
                payload = json.dumps(
                    {"text": doc.page_content, "metadata": doc.metadata},
                    sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                )
                chunk_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
                documents_by_id[chunk_id] = doc
            corpus_id = hashlib.sha256(
                "\n".join(sorted(documents_by_id)).encode("ascii")
            ).hexdigest()
            vector_store = Chroma(
                embedding_function=self.embeddings,
                persist_directory=settings.CHROMA_DB_PATH,
                collection_name=f"{settings.embedding_collection_name}-corpus-{corpus_id}",
            )
            existing_ids = set(vector_store.get(include=[])["ids"])
            missing_ids = sorted(set(documents_by_id) - existing_ids)
            # Stable IDs allow cached indices to be reused without adding copies.
            for start in range(0, len(missing_ids), 128):
                batch_ids = missing_ids[start:start + 128]
                vector_store.add_documents(
                    [documents_by_id[chunk_id] for chunk_id in batch_ids], ids=batch_ids,
                )

            logger.info("Vector store created successfully.")

            # Create BM25 retriever
            bm25 = BM25Retriever.from_documents(list(documents_by_id.values()))

            logger.info("BM25 retriever created successfully.")

            # Create vector-based retriever
            vector_retriever = vector_store.as_retriever(
                search_kwargs={
                    "k": settings.VECTOR_SEARCH_K
                }
            )

            logger.info("Vector retriever created successfully.")

            # Combine BM25 and vector retriever
            hybrid_retriever = EnsembleRetriever(
                retrievers=[
                    bm25,
                    vector_retriever
                ],
                weights=settings.HYBRID_RETRIEVER_WEIGHTS
            )

            logger.info("Hybrid retriever created successfully.")

            return hybrid_retriever

        except Exception as e:
            logger.error(
                f"Failed to build hybrid retriever: {e}"
            )
            raise
