# AI Project Cost Estimator

## Local Demo (safe API key usage)

1. Create local secrets file (not committed):
   `cp .streamlit/secrets.example.toml .streamlit/secrets.toml`
2. Put your real key in `.streamlit/secrets.toml`.
3. Run app:
   `streamlit run streamlit_app.py`

The app reads `OPENAI_API_KEY` from environment first, then from `.streamlit/secrets.toml`.
