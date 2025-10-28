
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

**Purpose:** Identify **information needs** before drafting.
**Focus:** Generate search queries, collect supporting evidence, stats, and expert quotes.
**Example Queries:**

```
"Latest inflation rate EU September 2025 site:ec.europa.eu"
"ECB response inflation 2025 analysis"
"European consumer price index breakdown 2025"
```

---

### 3. Generation Agent (`generation_node`)

**Purpose:** Produce the **initial draft** using the outline and research.
**Focus:** Write coherent paragraphs, integrate data, maintain style and flow.
**Example Output:**

```
The European Union is currently experiencing a gradual decline in inflation after peaking in early 2024. Experts attribute this moderation to tighter monetary policy and lower energy prices…
```

---

### 4. Reflection Agent (`reflection_node`)

**Purpose:** Review the draft and provide **detailed critique**.
**Focus:** Logic, clarity, style, argument strength, completeness.
**Example Output:**

```
The section on ECB policy lacks quantitative data. Add more comparison with US inflation. Improve transition between causes and effects.
```

---

### 5. Research Critique Agent (`research_critique_node`)

**Purpose:** Conduct **targeted research** based on the reflection feedback.
**Focus:** Generate queries to fill content gaps, collect updated statistics and relevant facts.
**Example Queries:**

```
"ECB interest rate changes 2024–2025 chart"
"EU inflation comparison US 2025 data"
```

---

## 🔁 Agent Workflow Cycle

```
![AI Report Workflow](asset/workflow.png)
```

At each iteration:

* Reports become **more complete and accurate**
* Structure becomes **tighter**
* Style and arguments become **more professional**

---

## ⚙️ Technical Requirements

* Python 3.8+
* See [requirements.txt](requirements.txt) for packages

---

## 🛠 Setup

1. Create and activate a virtual environment:

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

```bash
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
export TAVILY_API_KEY="YOUR_TAVILY_KEY"
# or use Gemini API key
export GEMINI_API_KEY="YOUR_GEMINI_KEY"
```

---

## 🧩 Usage

```python
from multi_agent_system import graph, AgentState

initial_state = {
    "task": "Write a detailed report about the latest inflation trends in the European Union.",
    "max_revisions": 2,
    "revision_number": 1,
    "content": [],
    "start_time": "2025-10-28T22:00:00",
    "logs": []
}

thread = {"configurable": {"thread_id": "1"}}

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

---

## 📚 References

* [LangGraph Docs](https://docs.langgraph.com)
* [LangChain Core](https://www.langchain.com)
* [Tavily API](https://tavily.com/docs)
* [Google Gemini API](https://ai.google.dev/gemini-api/docs/)

---

⭐ Support & Feedback

If you like what we are building here and want to support the project, the easiest way is to hit the ⭐ Star button on GitHub.

Your support helps us improve this multi-agent AI system and keep building useful tools for research and report generation.

Thank you! 🙏

[⭐ Star this project on GitHub](https://github.com/etheal9/Multi-Agent AI Report System with LangGraph) – Thank you for your support!

