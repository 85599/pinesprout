# PineSprout Studio (Streamlit App)

A browser UI on top of PineSprout: describe a strategy in plain English
and get a full Pine Script back (AI), pick a ready-made template like
**Daily/Weekly/Monthly Pivot Points + Confluence Zones**, or paste/upload
a script you already have — then lint, format, analyze, optimize,
explain, upgrade, and document it, all with one-click downloads.

## Run it locally

```bash
pip install -e ".[dev]"        # installs PineSprout + Streamlit
streamlit run streamlit_app.py
```

Open the URL it prints (usually `http://localhost:8501`).

If you want to use the "✨ Describe my strategy (AI)" mode, either:
- paste your Anthropic API key into the sidebar field each session, or
- set it once as an environment variable before launching:
  ```bash
  export ANTHROPIC_API_KEY="sk-ant-..."
  streamlit run streamlit_app.py
  ```

Everything else (templates, lint, format, analyze, optimize, explain,
upgrade, docs) works **fully offline**, no API key needed.

## Deploy on Streamlit Community Cloud

1. Push this repository to GitHub (public or private).
2. Go to [share.streamlit.io](https://share.streamlit.io) and click
   **New app**.
3. Select your repo/branch, and set:
   - **Main file path:** `streamlit_app.py`
   - Python version: 3.12 (Advanced settings)
4. Click **Deploy**. Streamlit Cloud installs everything from the root
   `requirements.txt` (which does `-e .` — installing PineSprout itself
   from `pyproject.toml` — plus `streamlit`).
5. (Optional, for AI generation) Add your key under **Settings → Secrets**:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-..."
   ```
   and either paste it into the sidebar at runtime, or wire
   `st.secrets["ANTHROPIC_API_KEY"]` into `os.environ` near the top of
   `streamlit_app.py` (a ready-to-uncomment snippet is in
   `.streamlit/secrets.toml.example`) so it's picked up automatically.

That's it — the app is live at `https://<your-app-name>.streamlit.app`.

## Deploy elsewhere (Docker / any host)

```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -e .
RUN pip install streamlit
EXPOSE 8501
CMD ["streamlit", "run", "streamlit_app.py", "--server.address=0.0.0.0", "--server.headless=true"]
```

```bash
docker build -t pinesprout-studio .
docker run -p 8501:8501 -e ANTHROPIC_API_KEY="sk-ant-..." pinesprout-studio
```

## What's in the app

| Mode | What it does | Needs API key? |
|---|---|---|
| ✨ Describe my strategy (AI) | Natural-language prompt → complete Pine Script via Claude | Yes |
| 📋 Use a template | Deterministic scaffolds: EMA cross, RSI, **Pivot Points + Confluence**, blanks | No |
| 📄 Paste / upload a script | Bring an existing `.pine` file | No |

Once you have a script loaded, the workbench tabs cover:

- **Code** — view + download the raw source
- **🔍 Lint** — unused vars, repaint risk, deprecated syntax, performance, style
- **🧹 Format** — preview + apply deterministic formatting
- **📊 Analyze** — complexity score, structure metrics, warnings
- **⚡ Optimize** — refactor suggestions (repeated calls, magic numbers, redundant booleans)
- **💬 Explain** — plain-English summary + line-by-line walkthrough
- **⬆️ Upgrade** — migrate v4 → v5 → v6 with one click
- **📄 Docs** — generate README.md, Markdown/HTML docs, or a full analysis report

## About the Pivot Points + Confluence template

This is the template built specifically for daily-levels-style trading:

- Calculates **classic pivot points** (PP, R1–R3, S1–S3) for **daily,
  weekly, and monthly** periods via `request.security(..., lookahead=
  barmerge.lookahead_off)` — explicitly repaint-safe.
- **Confluence detection**: on the last bar, it collects every enabled
  level across all three timeframes and flags any price zone where at
  least `minTouches` (default 2) independent levels land within your
  chosen tolerance (`confluenceTolPct`, default 0.15% of price) of each
  other — drawing a dashed purple line and a label listing which levels
  are stacking there (e.g. `"Confluence: D-R1 + W-PP"`).
- Ships with built-in alerts for crosses of the daily PP, R1, and S1.

Generate it, tweak the title/inputs in TradingView after pasting it in,
or use the **Optimize**/**Explain** tabs first to understand every line
before you trade off it.
