# AI Healthcare Agent (LangGraph)

Starter scaffold for a healthcare assistant powered by LangGraph with LangSmith tracing, Gemini LLMs, Pinecone vector search, and Supabase/Postgres persistence hooks.

## Prerequisites
- Python 3.10+
- `pip` and `python -m venv`

## Setup
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the project root (already populated here) and keep it out of source control.

## Run the sample graph
```bash
python -m app.entrypoints.main
```

The sample run streams states from the LangGraph workflow. LangSmith tracing is enabled via the provided environment variables.

## Project layout
- `app/core/config.py` - Settings loader (LangSmith, Pinecone, Supabase, Gemini).
- `app/clients/vector_store.py` - Pinecone vector store builder with Gemini embeddings.
- `app/workflows/healthcare_graph.py` - LangGraph workflow: retrieval node + answer node.
- `app/entrypoints/main.py` - CLI entrypoint showing a simple streaming invocation.

## Notes
- Update the Gemini model name or Pinecone index as needed for your account.
- If you plan to persist or retrieve from Supabase/Postgres, extend `app/clients/vector_store.py` or add a dedicated repository module.
