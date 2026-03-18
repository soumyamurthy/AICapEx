# AI Capex Project Copilot - Backend

This backend is built with **FastAPI** and serves synthetic capex project data, portfolio summaries, and an AI assistant endpoint.

## Setup

1. Create a Python virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. (Optional) Copy and configure environment variables:

```bash
cp .env.example .env
# Add your OPENAI_API_KEY to .env if you want real LLM responses
```

4. Run the app:

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Endpoints

- `GET /projects` - List all projects with computed risk and prediction flags
- `GET /projects/{project_id}` - Get a single project with related risks and recommendations
- `GET /portfolio/summary` - High-level portfolio metrics
- `GET /risks` - All risk items
- `POST /ask` - Ask the AI assistant a question

## Notes

- Synthetic data is generated automatically on first run and stored in `backend/data.json`.
- If you provide `OPENAI_API_KEY` in `.env`, the assistant will call OpenAI. Otherwise it uses a simple heuristic.
