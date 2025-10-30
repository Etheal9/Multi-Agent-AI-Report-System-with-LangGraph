
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

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your API keys (replace placeholders):

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
    "task": "Write a detailed report about the latest inflation trends in the European Union.",
    "max_revisions": 2,
    "revision_number": 1,
    "content": [],
    "start_time": "2025-10-28T22:00:00",
    "logs": []
}

thread = {"configurable": {"thread_id": "session-1"}}

for step in graph.stream(initial_state, thread):
    print(step)
```

* Each agent updates the `state` object
* `logs` field tracks progress and debug info
* Workflow stops automatically after `max_revisions`

---

## 📝 Advanced Features

* **Async streaming:** Optional `astream()` for real-time updates
* **Dynamic research:** Agents generate queries based on gaps in drafts
* **Iterative refinement:** Reflection + research critique loop ensures report quality
* **Memory / checkpointing:** Using `SqliteSaver` to resume work mid-process
* **Logging:** Each agent logs progress for easy debugging

---

## 🔧 Developer Notes

* You can **swap models** (OpenAI ↔ Gemini) without changing agent logic
* Customize **prompts** for different domains: finance, tech, policy, etc.
* Extend `Queries` model for structured search filters (date, source, type)
* Supports multi-threading for parallel research queries
* Agents are modular: add, remove, or replace nodes for custom workflows


## 📚 References

* [LangGraph Docs](https://www.langchain.com/langgraph)
* [LangChain Core](https://python.langchain.com/api_reference/core/index.html)
* [Tavily API](https://docs.tavily.com/)
* [Google Gemini API](https://ai.google.dev/gemini-api/docs)



⭐ Support & Feedback

If you like what we are building here and want to support the project, the easiest way is to hit the ⭐ Star button on GitHub.

Your support helps us improve this multi-agent AI system and keep building useful tools for research and report generation.

Thank you! 🙏

[⭐ Star this project on GitHub]( https://github.com/Etheal9/Multi-Agent-AI-Report-System-with-LangGraph?tab=readme-ov-file AI Report System with LangGraph) – Thank you for your support!

