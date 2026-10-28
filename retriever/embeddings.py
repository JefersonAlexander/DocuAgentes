from functools import lru_cache

from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer

from config.settings import settings


@lru_cache(maxsize=2)
def _load_embedding(model_name: str, device: str, cache_folder: str, batch_size: int):
    document_options = {"normalize_embeddings": True, "batch_size": batch_size}
    query_options = {"normalize_embeddings": True}
    if model_name == "intfloat/multilingual-e5-small":
        document_options["prompt"] = "passage: "
        query_options["prompt"] = "query: "
    return HuggingFaceEmbeddings(
        model_name=model_name,
        cache_folder=cache_folder,
        model_kwargs={"device": device, "trust_remote_code": False},
        encode_kwargs=document_options,
        query_encode_kwargs=query_options,
    )


def get_embedding():
    """Reuse a local multilingual encoder; no provider API key is needed."""
    return _load_embedding(
        settings.EMBEDDING_MODEL,
        settings.EMBEDDING_DEVICE,
        settings.MODEL_CACHE_DIR,
        settings.EMBEDDING_BATCH_SIZE,
    )


@lru_cache(maxsize=2)
def _load_tokenizer(model_name: str, cache_folder: str):
    return AutoTokenizer.from_pretrained(
        model_name, cache_dir=cache_folder, trust_remote_code=False
    )


def get_tokenizer():
    return _load_tokenizer(settings.EMBEDDING_MODEL, settings.MODEL_CACHE_DIR)
