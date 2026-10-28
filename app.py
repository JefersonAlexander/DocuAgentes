import gradio as gr
import hashlib
from typing import List, Dict
import os
from pathlib import Path
from uuid import uuid4

from document_processor.file_handler import DocumentProcessor, get_file_path
from retriever.builder import RetrieverBuilder
from agents.workflow import AgentWorkflow
from config import constants
from config.settings import settings
from utils.logging import logger

# 1) Define some example data 
#    (i.e. question + paths to documents relevant to that question).
EXAMPLES = {
    "Google 2024 Environmental Report": {
        "question": "Retrieve the data center PUE efficiency values in Singapore 2nd facility in 2019 and 2022. Also retrieve regional average CFE in Asia pacific in 2023",
        "file_paths": [str(Path(__file__).resolve().parent / "google-2024-environmental-report.pdf")]
    },
    "DeepSeek-R1 Technical Report": {
        "question": "Summarize DeepSeek-R1 model's performance evaluation on all coding tasks against OpenAI o1-mini model",
        "file_paths": [str(Path(__file__).resolve().parent / "DeepSeek Technical Report.pdf")]
    }
}

def main():
    processor = DocumentProcessor()
    retriever_builder = RetrieverBuilder()
    workflow = AgentWorkflow()

    # Define custom CSS for styling
    css = """
    .title {
        font-size: 1.5em !important; 
        text-align: center !important;
        color: #FFD700; 
    }

    .subtitle {
        font-size: 1em !important; 
        text-align: center !important;
        color: #FFD700; 
    }

    .text {
        text-align: center;
    }
    """

    js = """
    function createGradioAnimation() {
        var container = document.createElement('div');
        container.id = 'gradio-animation';
        container.style.fontSize = '2em';
        container.style.fontWeight = 'bold';
        container.style.textAlign = 'center';
        container.style.marginBottom = '20px';
        container.style.color = '#eba93f';

        var text = 'Welcome to DocChat 🐥!';
        for (var i = 0; i < text.length; i++) {
            (function(i){
                setTimeout(function(){
                    var letter = document.createElement('span');
                    letter.style.opacity = '0';
                    letter.style.transition = 'opacity 0.1s';
                    letter.innerText = text[i];

                    container.appendChild(letter);

                    setTimeout(function() {
                        letter.style.opacity = '0.9';
                    }, 50);
                }, i * 250);
            })(i);
        }

        var gradioContainer = document.querySelector('.gradio-container');
        gradioContainer.insertBefore(container, gradioContainer.firstChild);

        return 'Animation created';
    }
    """

    with gr.Blocks(title="DocChat 🐥") as demo:
        gr.Markdown("## DocChat: powered by Docling 🐥 and LangGraph", elem_classes="subtitle")
        gr.Markdown("# How it works ✨:", elem_classes="title")
        gr.Markdown("📤 Upload your document(s), enter your query then hit Submit 📝", elem_classes="text")
        gr.Markdown("Or you can select one of the examples from the drop-down menu, select Load Example then hit Submit 📝", elem_classes="text")
        gr.Markdown("⚠️ **Note:** DocChat only accepts documents in these formats: '.pdf', '.docx', '.txt', '.md'", elem_classes="text")

        # 2) Maintain the session state for retrieving doc changes
        session_state = gr.State({
            "file_hashes": frozenset(),
            "retriever": None,
            "revision": uuid4().hex,
        })

        # 3) Layout 
        with gr.Row():
            with gr.Column():
                # Section for Examples
                gr.Markdown("### Example 📂")
                example_dropdown = gr.Dropdown(
                    label="Select an Example 🐥",
                    choices=list(EXAMPLES.keys()),
                    value=None,  # initially unselected
                )
                load_example_btn = gr.Button("Load Example 🛠️")

                # Standard input components
                files = gr.Files(
                    label="📄 Upload Documents",
                    file_types=constants.ALLOWED_TYPES,
                    type="filepath",
                )
                question = gr.Textbox(label="❓ Question", lines=3)

                submit_btn = gr.Button("Submit 🚀")
                
            with gr.Column():
                answer_output = gr.Textbox(label="🐥 Answer", interactive=False)
                verification_output = gr.Textbox(label="✅ Verification Report")

        # 4) Helper function to load example into the UI
        def load_example(example_key: str):
            """
            Given a key like 'Example 1', 
            read the relevant docs from disk and return
            them as file-like objects, plus the example question.
            """
            if not example_key or example_key not in EXAMPLES:
                return [], ""  # blank if not found

            ex_data = EXAMPLES[example_key]
            question = ex_data["question"]
            file_paths = ex_data["file_paths"]

            # Prepare the file list to return. We read them from disk to
            # give Gradio something it can handle as "uploaded" files.
            loaded_files = []
            for path in file_paths:
                if os.path.exists(path):
                    # Gradio can accept a path directly, or a file-like object
                    loaded_files.append(path)
                else:
                    logger.warning(f"File not found: {path}")

            # The function can return lists matching the outputs we define below
            return loaded_files, question

        load_example_btn.click(
            fn=load_example,
            inputs=[example_dropdown],
            outputs=[files, question]
        )

        # 5) Standard flow for question submission
        def process_question(question_text: str, uploaded_files: List, state: Dict):
            """Handle questions with document caching."""
            revision = state.setdefault("revision", uuid4().hex)
            try:
                if not question_text.strip():
                    raise ValueError("❌ Question cannot be empty")
                if not uploaded_files:
                    clear_document_session(state)
                    revision = state["revision"]
                    raise ValueError("❌ No documents uploaded")

                try:
                    current_hashes = _get_file_hashes(uploaded_files)
                except Exception:
                    clear_document_session(state)
                    revision = state["revision"]
                    raise
                
                if state["retriever"] is None or current_hashes != state["file_hashes"]:
                    # Drop the previous retriever before processing: a failed new
                    # upload must not leave the previous document active.
                    clear_document_session(state)
                    revision = state["revision"]
                    logger.info("Processing new/changed documents...")
                    chunks = processor.process(uploaded_files)
                    retriever = retriever_builder.build_hybrid_retriever(chunks)
                    if state["revision"] != revision:
                        return gr.skip(), gr.skip(), gr.skip()
                    
                    state.update({
                        "file_hashes": current_hashes,
                        "retriever": retriever
                    })
                
                result = workflow.full_pipeline(
                    question=question_text,
                    retriever=state["retriever"]
                )
                if state["revision"] != revision:
                    return gr.skip(), gr.skip(), gr.skip()
                
                return result["draft_answer"], result["verification_report"], state
                    
            except Exception as e:
                if state["revision"] != revision:
                    return gr.skip(), gr.skip(), gr.skip()
                logger.error(f"Processing error: {str(e)}")
                return f"❌ Error: {str(e)}", "", state

        submit_event = submit_btn.click(
            fn=process_question,
            inputs=[question, files, session_state],
            outputs=[answer_output, verification_output, session_state]
        )
        # Also fires when Load Example replaces files programmatically.
        files.change(
            fn=clear_document_session,
            inputs=[session_state],
            outputs=[answer_output, verification_output, session_state],
            cancels=[submit_event],
            queue=False,
        )

    demo.launch(
        server_name="127.0.0.1",
        server_port=5000,
        share=settings.GRADIO_SHARE,
        theme=gr.themes.Citrus(),
        css=css,
        js=js,
    )

def _get_file_hashes(uploaded_files: List) -> frozenset:
    """Track both file contents and the source names shown in answers."""
    hashes = set()
    for file in uploaded_files:
        path = get_file_path(file)
        with path.open("rb") as f:
            hashes.add((path.name, hashlib.sha256(f.read()).hexdigest()))
    return frozenset(hashes)


def clear_document_session(state: Dict):
    """Invalidate retrieval and any in-flight answer when the files change."""
    state.update(file_hashes=frozenset(), retriever=None, revision=uuid4().hex)
    return "", "", state

if __name__ == "__main__":
    main()
