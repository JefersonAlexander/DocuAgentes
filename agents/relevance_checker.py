from enum import Enum

from config.llm import GroqServiceError, build_chat_model, invoke_chat_model

import logging

logger = logging.getLogger(__name__)


class RelevanceLabel(Enum):
    CAN_ANSWER = "CAN_ANSWER"
    PARTIAL = "PARTIAL"
    NO_MATCH = "NO_MATCH"


class RelevanceChecker:
    def __init__(self):
        self.llm = build_chat_model()

    def check(self, question: str, retriever, k=3) -> str:
        """
        1. Retrieve the top-k document chunks from the global retriever.
        2. Combine them into a single text string.
        3. Pass that text + question to Groq for classification.

        Returns:
            "CAN_ANSWER", "PARTIAL", or "NO_MATCH".
        """

        logger.debug(
            f"RelevanceChecker.check called with question='{question}' and k={k}"
        )

        # Retrieve document chunks
        top_docs = retriever.invoke(question)

        if not top_docs:
            logger.debug(
                "No documents returned from retriever.invoke(). "
                "Classifying as NO_MATCH."
            )
            return "NO_MATCH"

        # Combine the top-k chunks
        document_content = "\n\n".join(
            doc.page_content for doc in top_docs[:k]
        )

        prompt = f"""
You are an AI relevance checker between a user's question
and provided document content.

Classify how well the document content addresses the user's question.

Classification rules:

CAN_ANSWER:
The passages contain enough explicit information to fully answer
the question.

PARTIAL:
The passages mention or discuss the question's topic but do not
provide all the information required for a complete answer.

NO_MATCH:
The passages do not discuss or mention the question's topic.

Important:
If the passages mention or reference the topic or timeframe of the
question in any way, even if incomplete, classify it as PARTIAL
instead of NO_MATCH.

Return exactly one label: CAN_ANSWER, PARTIAL, or NO_MATCH.
Do not include explanations, quotes, or Markdown formatting.

Question:
{question}

Passages:
{document_content}
"""

        response = invoke_chat_model(self.llm, prompt)
        llm_response = response.content.strip().upper() if isinstance(response.content, str) else ""
        logger.debug(f"Groq response: {llm_response}")

        print(f"Checker response: {llm_response}")

        valid_labels = {label.value for label in RelevanceLabel}

        if llm_response not in valid_labels:
            logger.warning(
                f"Groq returned unexpected classification: {llm_response}"
            )
            raise GroqServiceError(
                "Groq devolvió una clasificación no válida. "
                "Reintenta la consulta o aumenta GROQ_MAX_TOKENS en .env."
            )

        return llm_response
