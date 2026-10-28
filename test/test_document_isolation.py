"""Regression checks for changing the active documents, without provider calls."""

import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class DocumentIndexIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        environment = patch.dict(os.environ, {
            "GROQ_API_KEY": "test-groq-key",
            "HF_HUB_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
            "ANONYMIZED_TELEMETRY": "False",
        })
        environment.start()
        cls.addClassCleanup(environment.stop)

    def setUp(self):
        from config.settings import settings
        from langchain_core.documents import Document
        from langchain_core.embeddings import DeterministicFakeEmbedding
        from retriever.builder import RetrieverBuilder

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(self.stop_chroma)
        directory = patch.object(settings, "CHROMA_DB_PATH", str(Path(temporary.name) / "chroma"))
        directory.start()
        self.addCleanup(directory.stop)
        self.embedding = DeterministicFakeEmbedding(size=16)
        factory = patch("retriever.builder.get_embedding", return_value=self.embedding)
        factory.start()
        self.addCleanup(factory.stop)
        self.builder = RetrieverBuilder()
        self.report_a = Document(
            page_content="ALPHA: This document discusses data center energy consumption.",
            metadata={"source": "environment.md"},
        )
        self.report_b = Document(
            page_content="BETA: This document describes password reset procedures.",
            metadata={"source": "passwords.md"},
        )
        self.report_c = Document(
            page_content="GAMMA: This document describes camera maintenance.",
            metadata={"source": "cameras.md"},
        )

    @staticmethod
    def stop_chroma():
        from chromadb.api.client import SharedSystemClient
        for system in list(SharedSystemClient._identifier_to_system.values()):
            system.stop()
        SharedSystemClient.clear_system_cache()

    def test_replacing_document_returns_only_current_document(self):
        self.builder.build_hybrid_retriever([self.report_a])
        current = self.builder.build_hybrid_retriever([self.report_b])
        result = current.invoke("What is this document about?")
        self.assertTrue(result)
        self.assertEqual({doc.metadata["source"] for doc in result}, {"passwords.md"})

    def test_existing_retriever_remains_bound_to_its_documents(self):
        first = self.builder.build_hybrid_retriever([self.report_a])
        self.builder.build_hybrid_retriever([self.report_b])
        self.assertEqual(
            {doc.metadata["source"] for doc in first.invoke("document")},
            {"environment.md"},
        )

    def test_multiple_active_documents_exclude_previously_loaded_document(self):
        self.builder.build_hybrid_retriever([self.report_c])
        current = self.builder.build_hybrid_retriever([self.report_a, self.report_b])
        self.assertEqual(
            {doc.metadata["source"] for doc in current.invoke("document")},
            {"environment.md", "passwords.md"},
        )

    def test_reloading_same_documents_does_not_duplicate_or_reembed(self):
        first = self.builder.build_hybrid_retriever([self.report_a, self.report_b])
        first_ids = set(first.retrievers[1].vectorstore.get(include=[])["ids"])
        with patch.object(type(self.embedding), "embed_documents", side_effect=AssertionError("Unnecessary reindex")):
            second = self.builder.build_hybrid_retriever([self.report_b, self.report_a])
        second_ids = set(second.retrievers[1].vectorstore.get(include=[])["ids"])
        self.assertEqual(first_ids, second_ids)
        self.assertEqual(len(second_ids), 2)


class DocumentUploadIsolationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        environment = patch.dict(os.environ, {
            "GROQ_API_KEY": "test-groq-key",
            "GRADIO_ANALYTICS_ENABLED": "False",
            "HF_HUB_OFFLINE": "1",
            "HF_HUB_DISABLE_TELEMETRY": "1",
        })
        environment.start()
        cls.addClassCleanup(environment.stop)

    def setUp(self):
        from config.settings import settings

        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        override = patch.object(settings, "CACHE_DIR", str(self.root / "cache"))
        override.start()
        self.addCleanup(override.stop)
        self.first = self.root / "first.md"
        self.first.write_text("First report: 42 incidents.", encoding="utf-8")
        self.second = self.root / "second.md"
        self.second.write_text("Second report: 53 cameras.", encoding="utf-8")

    def callbacks(self):
        import app
        import gradio as gr
        from langchain_core.documents import Document

        for name in ("DocumentProcessor", "RetrieverBuilder", "AgentWorkflow"):
            factory = patch.object(app, name)
            mocked = factory.start()
            self.addCleanup(factory.stop)
            setattr(self, name, mocked.return_value)
        self.DocumentProcessor.process.side_effect = lambda files: [
            Document(page_content=Path(file).read_text(encoding="utf-8")) for file in files
        ]
        self.RetrieverBuilder.build_hybrid_retriever.side_effect = lambda chunks: tuple(
            chunk.page_content for chunk in chunks
        )
        self.AgentWorkflow.full_pipeline.side_effect = lambda question, retriever: {
            "draft_answer": retriever[0], "verification_report": "Verified",
        }
        with patch.object(gr.Blocks, "launch", autospec=True) as launch:
            app.main()
        demo = launch.call_args.args[0]
        return {
            function.fn.__name__: function.fn
            for function in demo.fns.values() if function.fn is not None
        }

    def test_submission_after_replacement_uses_new_document(self):
        import app

        callbacks = self.callbacks()
        state = {"file_hashes": frozenset(), "retriever": None}
        submit = callbacks["process_question"]
        answer, _, _ = submit("What is it about?", [self.first], state)
        self.assertIn("42 incidents", answer)
        callbacks["clear_document_session"](state)
        answer, _, _ = submit("What is it about?", [self.second], state)
        self.assertIn("53 cameras", answer)
        self.assertNotIn("42 incidents", answer)
        self.assertEqual(state["file_hashes"], app._get_file_hashes([self.second]))

    def test_failed_replacement_drops_previous_retriever(self):
        callbacks = self.callbacks()
        state = {"file_hashes": frozenset(), "retriever": None}
        submit = callbacks["process_question"]
        submit("What is it about?", [self.first], state)
        self.AgentWorkflow.full_pipeline.reset_mock()
        self.DocumentProcessor.process.side_effect = ValueError("Unreadable PDF")
        answer, verification, _ = submit("What is it about?", [self.second], state)
        self.assertIn("Unreadable PDF", answer)
        self.assertEqual(verification, "")
        self.assertIsNone(state["retriever"])
        self.assertFalse(state["file_hashes"])
        self.AgentWorkflow.full_pipeline.assert_not_called()

    def test_changing_files_clears_outputs_and_invalidates_running_answer(self):
        import app
        import gradio as gr

        callbacks = self.callbacks()
        state = {"file_hashes": frozenset(), "retriever": None}

        def change_while_answering(**kwargs):
            answer, verification, _ = app.clear_document_session(state)
            self.assertEqual((answer, verification), ("", ""))
            return {"draft_answer": "Obsolete answer", "verification_report": "Obsolete"}

        self.AgentWorkflow.full_pipeline.side_effect = change_while_answering
        result = callbacks["process_question"]("What is it about?", [self.first], state)
        self.assertEqual(result, (gr.skip(), gr.skip(), gr.skip()))
        self.assertIsNone(state["retriever"])

    def test_removing_all_files_drops_previous_retriever(self):
        callbacks = self.callbacks()
        state = {"file_hashes": frozenset(), "retriever": object()}
        answer, _, _ = callbacks["process_question"]("Question", [], state)
        self.assertIn("No documents uploaded", answer)
        self.assertIsNone(state["retriever"])

    def test_cached_copy_uses_current_filename_without_reparsing(self):
        import app
        from document_processor.file_handler import DocumentProcessor
        from langchain_core.documents import Document

        self.second.write_bytes(self.first.read_bytes())
        processor = DocumentProcessor()
        with patch.object(processor, "_process_file", return_value=[
            Document(page_content="42 incidents", metadata={"source": self.first.name})
        ]) as parse:
            first = processor.process([self.first])
            second = processor.process([self.second])
        self.assertEqual(parse.call_count, 1)
        self.assertEqual(first[0].metadata["source"], self.first.name)
        self.assertEqual(second[0].metadata["source"], self.second.name)
        self.assertEqual(first[0].metadata["source_hash"], second[0].metadata["source_hash"])
        self.assertNotEqual(app._get_file_hashes([self.first]), app._get_file_hashes([self.second]))

    def test_processing_failure_does_not_silently_index_partial_selection(self):
        from document_processor.file_handler import DocumentProcessor
        from langchain_core.documents import Document

        processor = DocumentProcessor()
        with patch.object(processor, "_process_file", side_effect=[
            [Document(page_content="42 incidents")], ValueError("Unreadable file"),
        ]):
            with self.assertRaisesRegex(ValueError, "second.md.*Unreadable file"):
                processor.process([self.first, self.second])


if __name__ == "__main__":
    unittest.main()
