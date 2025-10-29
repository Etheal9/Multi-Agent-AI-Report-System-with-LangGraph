import os
import json
import sqlite3
from pathlib import Path
from typing import TypedDict, List
from dotenv import load_dotenv
from pydantic import BaseModel
from groq import Groq
from tavily import TavilyClient
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END

# === ENVIRONMENT SETUP ===
load_dotenv()

# --- API Keys ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

if not GROQ_API_KEY:
    raise EnvironmentError("❌ Missing GROQ_API_KEY in .env")
if not TAVILY_API_KEY:
    raise EnvironmentError("❌ Missing TAVILY_API_KEY in .env")

# --- Clients ---
client = Groq(api_key=GROQ_API_KEY)
tavily = TavilyClient(api_key=TAVILY_API_KEY)

# === MEMORY ===
conn = sqlite3.connect("memory.db", check_same_thread=False)
memory = SqliteSaver(conn=conn)

# === STATE ===
class AgentState(TypedDict):
    task: str
    plan: str
    draft: str
    critique: str
    content: List[str]
    revision_number: int
    max_revisions: int


# === MODEL CONFIG ===
MODEL = "openai/gpt-oss-120b"

# === PROMPTS ===
PLAN_PROMPT = """You are an expert report planner. Create a clear, structured outline for the topic provided."""

WRITER_PROMPT = """You are a professional report writer.
Generate or improve the report using the given content, plan, and critique if available.
------
{content}"""

REFLECTION_PROMPT = """You are a critical reviewer. Analyze the report and provide actionable feedback for improvement."""

RESEARCH_PLAN_PROMPT = """You are a research assistant. Based on the topic, return a JSON array of 1–3 search queries that would help gather relevant data."""

RESEARCH_CRITIQUE_PROMPT = """You are a researcher improving a report based on feedback. Generate up to 3 JSON search queries for new or missing data."""

# === STRUCTURED OUTPUT MODEL ===
class Queries(BaseModel):
    queries: List[str]


# === NODES ===
def safe_json_parse(text, fallback=None):
    """
    Safely parse LLM output — accepts JSON, Python dicts, YAML-like text, or plain strings.
    Ensures that data can flow between agents even if one returns natural text instead of JSON.
    """
    import json, ast, re

    if not text:
        return fallback or {"queries": []}

    # Remove code fences or markdown artifacts
    cleaned = re.sub(r"^```(json|python)?|```$", "", text.strip(), flags=re.MULTILINE)

    # Try JSON first
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Try Python dict style (single quotes, etc.)
    try:
        return ast.literal_eval(cleaned)
    except Exception:
        pass

    # Try to extract queries from text heuristically
    # Example: "queries: [“foo”, “bar”]" → {"queries": ["foo", "bar"]}
    match = re.search(r"\[([^\]]+)\]", cleaned)
    if match:
        items = [i.strip().strip('"').strip("'") for i in match.group(1).split(",")]
        return {"queries": items}

    print("⚠️ JSON parse failed, returning raw text as fallback.")
    return fallback or {"queries": [], "text": cleaned}


def plan_node(state: AgentState):
    messages = [
        {"role": "system", "content": PLAN_PROMPT},
        {"role": "user", "content": state["task"]}
    ]
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        return {"plan": response.choices[0].message.content}
    except Exception as e:
        return {"plan": f"[error: plan_node failed] {e}"}


def research_plan_node(state: AgentState):
    messages = [
        {"role": "system", "content": RESEARCH_PLAN_PROMPT},
        {"role": "user", "content": state["task"]}
    ]
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        queries_data = safe_json_parse(response.choices[0].message.content)
        #queries = Queries(queries=queries_data.get("queries", []))
        queries = Queries(queries=queries_data.get("queries", []) or queries_data.get("text", "").splitlines())

    except Exception as e:
        return {"content": [f"[error: research_plan_node] {e}"]}

    content = state.get("content", [])
    for q in queries.queries:
        try:
            search = tavily.search(query=q, max_results=2)
            for r in search.get("results", []):
                content.append(r.get("content", ""))
        except Exception as e:
            content.append(f"[search_error: {q}] {e}")
    return {"content": content}


def file_tool_node(state: AgentState):
    content = state.get("content", [])
    base_path = Path(__file__).parent if "__file__" in globals() else Path.cwd()
    asset_path = base_path / "assets" / "image.txt"

    if asset_path.exists():
        try:
            text = asset_path.read_text(encoding="utf-8")
            content.append(f"[file:{asset_path.name}]\n{text}")
        except Exception as e:
            content.append(f"[file_error:{asset_path.name}] {e}")
    else:
        content.append("[file_missing: assets/image.txt not found]")
    return {"content": content}


def compute_stats_node(state: AgentState):
    content = state.get("content", [])
    joined = "\n\n".join(content)
    words = len(joined.split()) if joined else 0
    sentences = [s for s in joined.replace("\n", " ").split(".") if s.strip()]
    num_sentences = len(sentences)
    avg_sent_len = (words / num_sentences) if num_sentences > 0 else 0
    summary = f"[stats] words={words}, sentences={num_sentences}, avg_words_per_sentence={avg_sent_len:.2f}"
    content.append(summary)
    return {
        "content": content,
        "stats": {"words": words, "sentences": num_sentences, "avg_sentence_words": avg_sent_len}
    }


def generation_node(state: AgentState):
    content = "\n\n".join(state.get("content", []))
    user_message = f"{state['task']}\n\nPlan:\n{state['plan']}"
    messages = [
        {"role": "system", "content": WRITER_PROMPT.format(content=content)},
        {"role": "user", "content": user_message}
    ]
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        return {
            "draft": response.choices[0].message.content,
            "revision_number": state.get("revision_number", 0) + 1
        }
    except Exception as e:
        return {"draft": f"[error: generation_node failed] {e}"}


def reflection_node(state: AgentState):
    messages = [
        {"role": "system", "content": REFLECTION_PROMPT},
        {"role": "user", "content": state.get("draft", "")}
    ]
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        return {"critique": response.choices[0].message.content}
    except Exception as e:
        return {"critique": f"[error: reflection_node failed] {e}"}


def research_critique_node(state: AgentState):
    messages = [
        {"role": "system", "content": RESEARCH_CRITIQUE_PROMPT},
        {"role": "user", "content": state.get("critique", "")}
    ]
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages)
        queries_data = safe_json_parse(response.choices[0].message.content)
        #queries = Queries(queries=queries_data.get("queries", []))
        queries = Queries(queries=queries_data.get("queries", []) or queries_data.get("text", "").splitlines())

    except Exception as e:
        return {"content": [f"[error: research_critique_node] {e}"]}

    content = state.get("content", [])
    for q in queries.queries:
        try:
            search = tavily.search(query=q, max_results=2)
            for r in search.get("results", []):
                content.append(r.get("content", ""))
        except Exception as e:
            content.append(f"[search_error: {q}] {e}")
    return {"content": content}


# === CONTROL FLOW ===
def should_continue(state: AgentState):
    if state.get("revision_number", 0) >= state.get("max_revisions", 0):
        return END
    return "reflect"


# === BUILD THE GRAPH ===
builder = StateGraph(AgentState)
builder.add_node("planner", plan_node)
builder.add_node("research_plan", research_plan_node)
builder.add_node("file_fetch", file_tool_node)
builder.add_node("compute_stats", compute_stats_node)
builder.add_node("generate", generation_node)
builder.add_node("reflect", reflection_node)
builder.add_node("research_critique", research_critique_node)

builder.set_entry_point("planner")

builder.add_conditional_edges("generate", should_continue, {END: END, "reflect": "reflect"})

builder.add_edge("planner", "research_plan")
builder.add_edge("research_plan", "file_fetch")
builder.add_edge("file_fetch", "compute_stats")
builder.add_edge("compute_stats", "generate")
builder.add_edge("reflect", "research_critique")
builder.add_edge("research_critique", "generate")

graph = builder.compile(checkpointer=memory)

# === RUN ===
thread = {"configurable": {"thread_id": "1"}} 

print("🚀 Starting AI Report Generator...\n")

for step in graph.stream({
    "task": "what different of the quantum machine",
    "max_revisions": 2,
    "revision_number": 0,
    "content": []
}, thread):
    print(step)
