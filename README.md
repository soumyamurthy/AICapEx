# AI Project Cost Estimator

## Local Demo (safe API key usage)

1. Create local secrets file (not committed):
   `cp .streamlit/secrets.example.toml .streamlit/secrets.toml`
2. Put your real key in `.streamlit/secrets.toml`.
3. Run app:
   `streamlit run streamlit_app.py`

The app reads `OPENAI_API_KEY` from environment first, then from `.streamlit/secrets.toml`.

## Publish On Streamlit Community Cloud

1. Open https://share.streamlit.io and sign in with GitHub.
2. Click `New app`.
3. Select repository: `soumyamurthy/AICapEx`.
4. Branch: `main`
5. Main file path: `streamlit_app.py`
6. In `Advanced settings` -> `Secrets`, add:

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-5"
```

7. Click `Deploy`.
