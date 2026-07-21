import json
import logging

import gradio as gr
import spaces

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GLINER_LABELS = ["person", "organization", "topic", "technology", "concept"]

_gliner_model = None
_embedding_model = None


def _load_gliner():
    global _gliner_model
    if _gliner_model is not None:
        return
    logger.info("Loading GLiNER2: fastino/gliner2-base-v1")
    from gliner2 import GLiNER2

    _gliner_model = GLiNER2.from_pretrained("fastino/gliner2-base-v1")
    logger.info("GLiNER2 loaded")


def _load_embedding():
    global _embedding_model
    if _embedding_model is not None:
        return
    logger.info("Loading MiniLM: all-MiniLM-L6-v2")
    from sentence_transformers import SentenceTransformer

    _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("MiniLM loaded")


@spaces.GPU
def extract_entities(text: str, labels: str) -> str:
    """
    Extract named entities. Returns flat entity list matching AutoLinks schema:
    [{"text": "Apple", "start": 0, "end": 5, "label": "COMPANY"}, ...]
    """
    _load_gliner()
    parsed_labels = json.loads(labels) if labels else GLINER_LABELS

    result = _gliner_model.extract_entities(
        text, parsed_labels, include_spans=True, include_confidence=False
    )

    entities = []
    for label_name, matches in result["entities"].items():
        for match in matches:
            if isinstance(match, dict):
                entities.append(
                    {
                        "text": match["text"],
                        "start": match["start"],
                        "end": match["end"],
                        "label": label_name.upper(),
                    }
                )
            else:
                entities.append(
                    {
                        "text": match,
                        "start": 0,
                        "end": len(match),
                        "label": label_name.upper(),
                    }
                )

    logger.info("Extracted %d entities", len(entities))
    return json.dumps(entities)


@spaces.GPU
def embed_text(texts: str) -> str:
    _load_embedding()
    parsed_texts = json.loads(texts) if texts else []
    vectors = _embedding_model.encode(parsed_texts, convert_to_numpy=True)
    embeddings = [vec.tolist() for vec in vectors]
    logger.info("Generated %d embeddings", len(embeddings))
    return json.dumps(embeddings)


def health() -> str:
    return json.dumps(
        {
            "status": "ok",
            "models": {
                "gliner": "loaded" if _gliner_model is not None else "not_loaded",
                "minilm": "loaded" if _embedding_model is not None else "not_loaded",
            },
            "gliner_labels": GLINER_LABELS,
        }
    )


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------
with gr.Blocks(title="AutoLinks Models v2") as demo:
    gr.Markdown("# AutoLinks Models v2")
    gr.Markdown("GLiNER2 entity extraction + MiniLM embeddings for AutoLinks.")
    gr.Markdown(
        "> API: `POST /gradio_api/call/extract_entities` | `POST /gradio_api/call/embed_text`"
    )

    with gr.Tab("Extract Entities"):
        extract_input = gr.Textbox(label="Text", lines=5, value="Apple CEO Tim Cook announced iPhone 15 in Cupertino yesterday.")
        extract_labels = gr.Textbox(
            label="Labels (JSON list)",
            value=json.dumps(GLINER_LABELS),
            lines=1,
        )
        extract_btn = gr.Button("Extract")
        extract_output = gr.Textbox(label="Entities (JSON)", lines=10)
        extract_btn.click(
            extract_entities,
            inputs=[extract_input, extract_labels],
            outputs=extract_output,
        )

    with gr.Tab("Embed Text"):
        embed_input = gr.Textbox(
            label="Texts (JSON list)", lines=3, value='["Hello world"]'
        )
        embed_btn = gr.Button("Embed")
        embed_output = gr.Textbox(label="Embeddings (JSON)", lines=8)
        embed_btn.click(embed_text, inputs=embed_input, outputs=embed_output)

    with gr.Tab("Health"):
        health_btn = gr.Button("Check")
        health_output = gr.Textbox(label="Status", lines=5)
        health_btn.click(health, inputs=[], outputs=health_output)


demo.launch()
