import os
import hashlib
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from docling.document_converter import DocumentConverter
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from retriever.embeddings import get_tokenizer
from config import constants
from config.settings import settings
from utils.logging import logger


def get_file_path(file) -> Path:
    """Accept Gradio filepath values and legacy file objects."""
    return Path(file if isinstance(file, (str, os.PathLike)) else file.name)


class DocumentProcessor:
    def __init__(self):
        self.headers = [("#", "Header 1"), ("##", "Header 2")]
        self.cache_dir = Path(settings.CACHE_DIR) / settings.embedding_fingerprint
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    def validate_files(self, files: List) -> None:
        """Validate the total size of the uploaded files."""
        total_size = sum(get_file_path(file).stat().st_size for file in files)
        if total_size > constants.MAX_TOTAL_SIZE:
            raise ValueError(f"Total size exceeds {constants.MAX_TOTAL_SIZE//1024//1024}MB limit")

    def process(self, files: List) -> List:
        """Process files with caching for subsequent queries"""
        self.validate_files(files)
        all_chunks = []
        seen_hashes = set()
        
        for file in files:
            file_path = get_file_path(file)
            try:
                # Generate content-based hash for caching
                with file_path.open("rb") as f:
                    file_hash = self._generate_hash(f.read())
                
                cache_path = self.cache_dir / f"{file_hash}.pkl"
                
                if self._is_cache_valid(cache_path):
                    logger.info(f"Loading from cache: {file_path}")
                    chunks = self._load_from_cache(cache_path)
                else:
                    logger.info(f"Processing and caching: {file_path}")
                    chunks = self._process_file(file)
                    self._save_to_cache(chunks, cache_path)

                if not chunks:
                    raise ValueError("No readable document fragments were produced")
                
                # Cached text can belong to a renamed upload. Always refresh its
                # provenance from the active file, including for older cache entries.
                for chunk in chunks:
                    chunk.metadata["source"] = file_path.name
                    chunk.metadata["source_hash"] = file_hash
                    chunk_hash = self._generate_hash(chunk.page_content.encode())
                    identity = (file_path.name, file_hash, chunk_hash)
                    if identity not in seen_hashes:
                        all_chunks.append(chunk)
                        seen_hashes.add(identity)
                        
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {str(e)}")
                raise ValueError(f"Could not process {file_path.name}: {e}") from e
                
        logger.info(f"Total unique chunks: {len(all_chunks)}")
        return all_chunks

    def _process_file(self, file) -> List:
        """Original processing logic with Docling"""
        file_path = get_file_path(file)
        if file_path.suffix.lower() not in constants.ALLOWED_TYPES:
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        converter = DocumentConverter()
        markdown = converter.convert(file_path).document.export_to_markdown()
        splitter = MarkdownHeaderTextSplitter(self.headers)
        sections = splitter.split_text(markdown)
        tokenizer = get_tokenizer()
        token_splitter = RecursiveCharacterTextSplitter.from_huggingface_tokenizer(
            tokenizer,
            chunk_size=settings.CHUNK_SIZE_TOKENS,
            chunk_overlap=settings.CHUNK_OVERLAP_TOKENS,
        )
        chunks = token_splitter.split_documents(sections)
        for chunk in chunks:
            chunk.metadata["source"] = file_path.name
            # Verify the complete encoded input, including prefixes and special tokens.
            prefix = "passage: " if settings.EMBEDDING_MODEL == "intfloat/multilingual-e5-small" else ""
            limit = 512 if prefix else 8192
            if len(tokenizer.encode(prefix + chunk.page_content, add_special_tokens=True)) > limit:
                raise ValueError("A document fragment exceeds the embedding model's token limit")
        return chunks

    def _generate_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def _save_to_cache(self, chunks: List, cache_path: Path):
        with open(cache_path, "wb") as f:
            pickle.dump({
                "timestamp": datetime.now().timestamp(),
                "chunks": chunks
            }, f)

    def _load_from_cache(self, cache_path: Path) -> List:
        with open(cache_path, "rb") as f:
            data = pickle.load(f)
        return data["chunks"]

    def _is_cache_valid(self, cache_path: Path) -> bool:
        if not cache_path.exists():
            return False
            
        cache_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return cache_age < timedelta(days=settings.CACHE_EXPIRE_DAYS)
