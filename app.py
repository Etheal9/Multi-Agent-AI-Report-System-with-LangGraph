import os
import json
import sqlite3
from pathlib import Path
from typing import TypedDict, List
from dotenv import load_dotenv
from pydantic import BaseModel
from tavily import TavilyClient
#from langgraph.checkpoint import SqliteSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, END
from groq_client import ask_groq  # <- your Groq integration

# === ENVIRONMENT SETUP ===
load_dotenv()

# --- API Keys ---
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise EnvironmentError("❌ Missing TAVILY_API_KEY in .env")

# --- Clients ---
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

# === PROMPTS ===
from prompts import (
    PLAN_PROMPT,
    WRITER_PROMPT,
    REFLECTION_PROMPT,
    RESEARCH_PLAN_PROMPT,
    RESEARCH_CRITIQUE_PROMPT,
)

# === STRUCTURED OUTPUT MODEL ===
class Queries(BaseModel):
    queries: List[str]

# === HELPERS ===
def safe_json_parse(text, fallback=None):
    import json, ast, re

    if not text:
        return fallback or {"queries": []}

    cleaned = re.sub(r"^```(json|python)?|```$", "", text.strip(), flags=re.MULTILINE)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    try:
        return ast.literal_eval(cleaned)
    except Exception:
        pass

    match = re.search(r"\[([^\]]+)\]", cleaned)
    if match:
        items = [i.strip().strip('"').strip("'") for i in match.group(1).split(",")]
        return {"queries": items}

    return fallback or {"queries": [], "text": cleaned}

# === NODES ===
def plan_node(state: AgentState):
    prompt_text = f"{PLAN_PROMPT}\n\nTask: {state['task']}"
    try:
        plan_text = ask_groq(prompt_text, max_tokens=500)
        return {"plan": plan_text}
    except Exception as e:
        return {"plan": f"[error: plan_node failed] {e}"}

def research_plan_node(state: AgentState):
    prompt_text = f"{RESEARCH_PLAN_PROMPT}\n\nTask: {state['task']}"
    try:
        response_text = ask_groq(prompt_text, max_tokens=300)
        queries_data = safe_json_parse(response_text)
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
    user_message = f"{state['task']}\n\nPlan:\n{state.get('plan', '')}"
    prompt_text = WRITER_PROMPT.format(content=content) + "\n\n" + user_message
    try:
        draft_text = ask_groq(prompt_text, max_tokens=1000)
        return {
            "draft": draft_text,
            "revision_number": state.get("revision_number", 0) + 1
        }
    except Exception as e:
        return {"draft": f"[error: generation_node failed] {e}"}

def reflection_node(state: AgentState):
    prompt_text = f"{REFLECTION_PROMPT}\n\nDraft:\n{state.get('draft', '')}"
    try:
        critique_text = ask_groq(prompt_text, max_tokens=500)
        return {"critique": critique_text}
    except Exception as e:
        return {"critique": f"[error: reflection_node failed] {e}"}

def research_critique_node(state: AgentState):
    prompt_text = f"{RESEARCH_CRITIQUE_PROMPT}\n\nCritique:\n{state.get('critique', '')}"
    try:
        response_text = ask_groq(prompt_text, max_tokens=300)
        queries_data = safe_json_parse(response_text)
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
    """
    Safety-first stopping:
    - stop when revision_number >= max_revisions
    - stop if many loop iterations happen without progress (safety counter)
    - increment a safety loop counter stored in state['_loop_counter']
    """
    # ensure keys exist
    state.setdefault("revision_number", 0)
    state.setdefault("max_revisions", 1)
    loop_counter = state.get("_loop_counter", 0) + 1
    state["_loop_counter"] = loop_counter

    # Stop if revisions have reached or exceeded max_revisions
    if state.get("revision_number", 0) >= state.get("max_revisions", 0):
        print(f"✅ should_continue: reached revision limit ({state['revision_number']} >= {state['max_revisions']})")
        return END

    # Safety stop: if we loop too many times without progress, stop
    # (tunable: here we allow up to max_revisions*4 iterations)
    safety_limit = max(10, state.get("max_revisions", 1) * 4)
    if loop_counter > safety_limit:
        print(f"⚠️ should_continue: safety loop limit reached ({loop_counter} > {safety_limit}), stopping.")
        return END

    # Otherwise request the reflect step
    print(f"🔁 should_continue: loop {loop_counter}, revisions {state.get('revision_number', 0)} -> continuing to 'reflect'")
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

# === COMPILE THE GRAPH WITH RECURSION LIMIT ===
graph = builder.compile(checkpointer=memory)
graph.config = {"recursion_limit": 10}



#