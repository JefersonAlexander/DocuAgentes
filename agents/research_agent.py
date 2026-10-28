from typing import Dict, List
from langchain_core.documents import Document

from config.llm import build_chat_model, invoke_chat_model


class ResearchAgent:
    def __init__(self):
        """
        Initialize the research agent with Groq.
        """
        self.llm = build_chat_model()

    def sanitize_response(self, response_text: str) -> str:
        """
        Sanitize the LLM's response by stripping unnecessary whitespace.
        """
        return response_text.strip()

    def generate_prompt(self, question: str, context: str) -> str:
        """
        Generate a structured prompt for the LLM to generate
        a precise and factual answer.
        """
        prompt = f"""
        You are an AI assistant designed to provide precise and factual
        answers based on the given context.

        **Instructions:**
        - Answer the following question using only the provided context.
        - Be clear, concise, and factual.
        - Return as much information as you can get from the context.

        **Question:** {question}

        **Context:**
        {context}

        **Provide your answer below:**
        """

        return prompt

    def generate(self, question: str, documents: List[Document]) -> Dict:
        """
        Generate an initial answer using the provided documents.
        """
        print(
            f"ResearchAgent.generate called with question='{question}' "
            f"and {len(documents)} documents."
        )

        # Combine the document contents into one string
        context = "\n\n".join(
            [doc.page_content for doc in documents]
        )

        print(f"Combined context length: {len(context)} characters.")

        # Create prompt
        prompt = self.generate_prompt(question, context)

        print("Prompt created for the LLM.")

        # Call Groq
        print("Sending prompt to Groq...")
        response = invoke_chat_model(self.llm, prompt)
        print("LLM response received.")

        # Extract response
        try:
            llm_response = response.content.strip()

            print(f"Raw LLM response:\n{llm_response}")

        except Exception as e:
            print(f"Unexpected response structure: {e}")

            llm_response = (
                "I cannot answer this question based on "
                "the provided documents."
            )

        # Sanitize response
        draft_answer = (
            self.sanitize_response(llm_response)
            if llm_response
            else
            "I cannot answer this question based on the provided documents."
        )

        print(f"Generated answer: {draft_answer}")

        return {
            "draft_answer": draft_answer,
            "context_used": context
        }
