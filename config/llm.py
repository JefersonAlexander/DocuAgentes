from langchain_groq import ChatGroq

from config.settings import settings


def build_chat_model() -> ChatGroq:
    """Create the chat model shared by the document agents."""
    options = {}
    if settings.GROQ_MODEL in {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}:
        options = {
            "reasoning_effort": "low",
            "model_kwargs": {"include_reasoning": False},
        }
    return ChatGroq(
        model=settings.GROQ_MODEL,
        temperature=0.5,
        max_tokens=settings.GROQ_MAX_TOKENS,
        api_key=settings.GROQ_API_KEY,
        **options,
    )


class GroqServiceError(RuntimeError):
    """A provider failure that must not be interpreted as document irrelevance."""


def invoke_chat_model(llm: ChatGroq, prompt: str):
    try:
        return llm.invoke(prompt)
    except Exception as error:
        status = getattr(error, "status_code", None)
        if status == 404:
            message = (
                "Groq no encuentra el modelo configurado o no permite acceder a él. "
                "Configura GROQ_MODEL en multiagents/.env con un modelo activo "
                "disponible para tu cuenta y reinicia la aplicación."
            )
        elif status in {401, 403}:
            message = "Groq rechazó el acceso. Revisa GROQ_API_KEY y los permisos del modelo."
        elif status == 429:
            message = "Groq alcanzó el límite de uso. Espera y vuelve a intentarlo."
        else:
            message = "No se pudo obtener una respuesta de Groq. Revisa la conexión y vuelve a intentarlo."
        raise GroqServiceError(message) from error
