
# Multi-Agent AI Report System with LangGraph

This project demonstrates a **multi-agent workflow** that uses a large language model (LLM) together with the **Tavily search tool** to research and write professional reports.
It can integrate **Google Gemini** via `google-generativeai` or OpenAI models.

Example use case: *Generate a report on the latest inflation figures in the European Union.*

---

## 📑 Report Types

This system is adaptable for:

* **Economic Reports:** Inflation, GDP, market trends
* **Business Analysis:** Industry outlooks, competitor research
* **Technical Reports:** AI, blockchain, or engineering topics
* **Policy & Research Papers:** Social issues, education, sustainability
* **Startup / Market Research:** Product analysis, growth strategies

> Essentially, any report requiring **research, reasoning, iterative refinement, and factual accuracy**.

Unlike raw web scraping, Tavily returns **searchable content snippets** that agents can integrate into drafts.

---

## 🧠 Purpose of the Agents

The workflow includes **five specialized agents**, each responsible for a stage in the research-writing cycle.

### 1. Planner Agent (`plan_node`)

**Purpose:** Generate a **structured outline** for the report.
**Focus:** Section titles, subtopics, flow, tone, and writing goals.
**Example Output:**

```
Introduction → Current EU Inflation Overview
Causes → Energy Prices, Wage Growth, Monetary Policy
Effects → Consumer Spending, Business Margins
Solutions → ECB Measures, Fiscal Adjustments
```

---

### 2. Research Planner Agent (`research_plan_node`)
```markdown
# Multi‑Agent AI Report System (LangGraph example)

A compact example that shows how to build a multi‑agent research + writing pipeline using a LangGraph-style state graph, a retrieval/search tool (Tavily), and a text generation model (Groq / Gemini / OpenAI).

This repo demonstrates a looped workflow where agents: plan → research → draft → critique → research more → revise.

Quick use cases: automated economic, business, or technical reports where iterative fact-checking and structured output matter.

---

## Highlights

- Modular agents implemented as graph nodes (planner, research planner, file tool, generator, reflector, research critic).
- Integrates a search tool (`Tavily`) to pull factual snippets into drafts.
- Uses a small SQLite-backed checkpointer for memory/resume.
- Prompts are kept in `prompts.py` and are designed for structured outputs (JSON) when appropriate.

---

## Prerequisites

- Python 3.8+
- A virtual environment (recommended)
- API keys for services you plan to use:
    - TAVILY_API_KEY (required for research retrieval)
    - GROQ_API_KEY or equivalent (if using Groq / model provider)
    - (Optional) GEMINI_API_KEY or OPENAI_API_KEY if you swap models

See `requirements.txt` for the Python dependencies.

---

## Install

Windows PowerShell (example):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate
pip install -r requirements.txt
```

Create a `.env` file in the project root or export environment variables in your shell. Example `.env`:

```text
TAVILY_API_KEY=your_tavily_key_here
GROQ_API_KEY=your_groq_key_here
# Optional (if you use Gemini/OpenAI):
GEMINI_API_KEY=...
OPENAI_API_KEY=...
```

---

## Run the chat UI (example)

This repository includes a small Gradio-based chat UI (`chat_interface.py`).

From PowerShell in the project root (with the venv active):

```powershell
# start the UI
python chat_interface.py
```

Open http://127.0.0.1:7860 in your browser (or the URL printed by Gradio).

Note: `chat_interface.py` calls `graph.stream(...)` and will print node progress to the server console.

---

## Typical usage (programmatic)

You can import the compiled `graph` from `app.py` and run the workflow programmatically. Example pattern (simplified):

```python
from app import graph

initial_state = {
        "task": "Write a 800–1200 word report about EU inflation through 2025.",
        "max_revisions": 2,
        "revision_number": 0,
        "content": []
}

thread = {"configurable": {"thread_id": "session-1"}}

for step in graph.stream(initial_state, thread):
        # step is a dict with node outputs (e.g. {'generate': {'draft': '...'}})
        print(step)

```

---

## Troubleshooting — common issues and fixes

- ModuleNotFoundError: No module named 'langgraph.checkpoint.sqlite'
    - Symptom: `python chat_interface.py` fails with `ModuleNotFoundError` pointing at `from langgraph.checkpoint.sqlite import SqliteSaver`.
    - Why: The `langgraph` package structure can differ by version. The example expects the `SqliteSaver` implementation at that path.
    - Fixes (pick one):
        1. Try installing a compatible `langgraph` version (or the repo branch/tag the example was developed against). Example:
             - pip install langgraph
             - or install from source if a GitHub branch is recommended.
        2. Edit `app.py` to import more defensively: `from langgraph.checkpoint import SqliteSaver` (or fall back to an internal simple SQLite wrapper). If you edit the code, restart the app.
        3. If you cannot get `SqliteSaver`, set `memory = None` and compile the graph without a checkpointer for testing (not recommended for production).

- Missing API keys or bad keys
    - Ensure `TAVILY_API_KEY` and `GROQ_API_KEY` (or your chosen model key) are set. The code raises clear errors if keys are missing.

- assets/image.txt missing
    - The `file_tool_node` reads `assets/image.txt`. Create that file (or change the node) if you expect local assets to be included in content.

- Long-running graph or hanging
    - Graphs can iterate multiple times. Tune `max_revisions` and `graph.config['recursion_limit']` to limit loops.

---

## Recommended small improvements (suggestions)

These are small, low-risk suggestions you can apply to improve robustness and developer experience:

1. Improve LangGraph import resilience: try `from langgraph.checkpoint import SqliteSaver` first and fall back to other paths. Add a helpful error message recommending a package version.
2. Add a minimal `README example .env.example` file with placeholder keys to help onboarding.
3. Add a `scripts/` folder with convenience scripts (start-dev.ps1) that activate the venv and run the app with the right environment.
4. Add a short `CONTRIBUTING.md` with guidance on test patterns and where to pin `langgraph` versions.
5. Add a simple unit test that imports `app.py` and checks `graph` compiles (mocking external APIs) to catch import/regression issues early.

---

## Developer notes & pointers

- Prompts are in `prompts.py` and designed to produce structured JSON when needed.
- `groq_client.py` wraps the Groq SDK and attempts to be resilient to SDK changes.
- `app.py` composes the state graph and nodes; modify or extend nodes to add functionality.

---

## Where to go next

- If you want help pinning `langgraph` to a working version or adding the defensive imports mentioned above, I can update `app.py` and add a small test + `.env.example` for you.

---

If this repo helped you, consider starring the original project on GitHub.

```
*Repository: Etheal9 / Multi-Agent-AI-Report-System-with-LangGraph*
```

```text
Last edited: 2025-10-29 — README rewritten for clarity and troubleshooting guidance.
```

```


If you like what we are building here and want to support the project, the easiest way is to hit the ⭐ Star button on GitHub.
