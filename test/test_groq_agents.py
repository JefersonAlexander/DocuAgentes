"""Provider migration checks using simulated Groq responses, without API calls."""

import importlib.util
import io
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from contextlib import redirect_stdout


ROOT = Path(__file__).resolve().parents[1]


def load_module(name, relative_path):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class GroqAgentTests(unittest.TestCase):
    def setUp(self):
        # Isolate optional dependencies so checks can run before installation.
        groq = ModuleType("langchain_groq")
        groq.ChatGroq = MagicMock()
        settings = ModuleType("config.settings")
        settings.settings = SimpleNamespace(
            GROQ_API_KEY="test-groq-key", GROQ_MODEL="openai/gpt-oss-20b", GROQ_MAX_TOKENS=1024
        )
        self.settings = settings.settings
        documents = ModuleType("langchain_core.documents")
        documents.Document = SimpleNamespace
        self.modules = patch.dict(sys.modules, {
            "config": ModuleType("config"),
            "config.settings": settings,
            "langchain_groq": groq,
            "langchain_core": ModuleType("langchain_core"),
            "langchain_core.documents": documents,
        })
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.output = redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        self.constructor = groq.ChatGroq
        self.llm = self.constructor.return_value
        self.llm_module = load_module("config.llm", "config/llm.py")
        self.research = load_module(
            "groq_test_research", "agents/research_agent.py"
        ).ResearchAgent
        self.verification = load_module(
            "groq_test_verification", "agents/verification_agent.py"
        ).VerificationAgent
        self.relevance = load_module(
            "groq_test_relevance", "agents/relevance_checker.py"
        ).RelevanceChecker
        self.docs = [SimpleNamespace(page_content="The report records 42 cases.")]

    def test_all_agents_use_requested_model_and_parameters(self):
        for agent_type in [self.research, self.verification, self.relevance]:
            with self.subTest(agent=agent_type.__name__):
                agent_type()
                self.constructor.assert_called_with(
                    model="openai/gpt-oss-20b",
                    temperature=0.5,
                    max_tokens=1024,
                    api_key="test-groq-key",
                    reasoning_effort="low",
                    model_kwargs={"include_reasoning": False},
                )

    def test_research_uses_message_content_and_document_context(self):
        self.llm.invoke.return_value = SimpleNamespace(content="  42 cases.  ")
        result = self.research().generate("How many cases?", self.docs)
        self.assertEqual(result["draft_answer"], "42 cases.")
        prompt = self.llm.invoke.call_args.args[0]
        self.assertIn("How many cases?", prompt)
        self.assertIn(self.docs[0].page_content, prompt)

    def test_research_preserves_empty_response_fallback(self):
        self.llm.invoke.return_value = SimpleNamespace(content=" ")
        result = self.research().generate("How many cases?", self.docs)
        self.assertIn("cannot answer", result["draft_answer"])

    def test_inference_failures_are_reported(self):
        self.llm.invoke.side_effect = RuntimeError("Provider unavailable")
        with self.assertRaisesRegex(self.llm_module.GroqServiceError, "Groq"):
            self.research().generate("How many cases?", self.docs)
        with self.assertRaisesRegex(self.llm_module.GroqServiceError, "Groq"):
            self.verification().check("42 cases.", self.docs)
        retriever = MagicMock()
        retriever.invoke.return_value = self.docs
        with self.assertRaises(self.llm_module.GroqServiceError):
            self.relevance().check("How many cases?", retriever)

    def test_model_and_budget_can_be_overridden(self):
        self.settings.GROQ_MODEL = "configured-model"
        self.settings.GROQ_MAX_TOKENS = 2048
        self.research()
        self.constructor.assert_called_with(
            model="configured-model", temperature=0.5, max_tokens=2048, api_key="test-groq-key"
        )

    def test_provider_status_errors_explain_how_to_recover(self):
        for status, hint in [(404, "GROQ_MODEL"), (401, "GROQ_API_KEY"), (403, "permisos"), (429, "límite")]:
            with self.subTest(status=status):
                error = RuntimeError("Provider error details")
                error.status_code = status
                self.llm.invoke.side_effect = error
                with self.assertRaisesRegex(self.llm_module.GroqServiceError, hint):
                    self.llm_module.invoke_chat_model(self.llm, "Synthetic question")

    def test_verification_reads_message_content(self):
        self.llm.invoke.return_value = SimpleNamespace(content=(
            "Supported: YES\nUnsupported Claims: []\nContradictions: []\n"
            "Relevant: YES\nAdditional Details: Evidence found"
        ))
        result = self.verification().check("42 cases.", self.docs)
        self.assertIn("**Supported:** YES", result["verification_report"])
        self.assertIn("**Relevant:** YES", result["verification_report"])
        self.assertEqual(result["context_used"], self.docs[0].page_content)
        self.assertIn("42 cases.", self.llm.invoke.call_args.args[0])

    def test_verification_preserves_empty_response_fallback(self):
        self.llm.invoke.return_value = SimpleNamespace(content="")
        result = self.verification().check("42 cases.", self.docs)
        self.assertIn("**Supported:** NO", result["verification_report"])
        self.assertIn("Empty response", result["verification_report"])

    def test_relevance_accepts_only_classification_labels(self):
        retriever = MagicMock()
        retriever.invoke.return_value = self.docs
        checker = self.relevance()
        for label in ["CAN_ANSWER", "PARTIAL", "NO_MATCH"]:
            with self.subTest(label=label):
                self.llm.invoke.return_value = SimpleNamespace(
                    content=f"  {label.lower()}\n"
                )
                self.assertEqual(checker.check("How many?", retriever), label)
        self.llm.invoke.return_value = SimpleNamespace(content="I think so.")
        with self.assertRaisesRegex(self.llm_module.GroqServiceError, "clasificación"):
            checker.check("How many?", retriever)
        self.assertIn("Return exactly one label", self.llm.invoke.call_args.args[0])

    def test_no_documents_does_not_call_groq(self):
        retriever = MagicMock()
        retriever.invoke.return_value = []
        self.assertEqual(self.relevance().check("How many?", retriever), "NO_MATCH")
        self.llm.invoke.assert_not_called()


if __name__ == "__main__":
    unittest.main()
