import os
import json
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from tavily import TavilyClient
from pathlib import Path
from groq_client import ask_groq
from prompts import (
    PLAN_PROMPT,
    WRITER_PROMPT,
    REFLECTION_PROMPT,
    RESEARCH_PLAN_PROMPT,
    RESEARCH_CRITIQUE_PROMPT,
)

tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY", ""))

def safe_json_parse(text: str, fallback=None):
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


@tool
def expert_planner_skill(topic: str) -> str:
    """
    Use this skill to create a professional PRD/report outline before beginning research and writing.
    Returns a comprehensive outline mapped to the task topic.
    """
    prompt_text = f"{PLAN_PROMPT}\n\nTask: {topic}"
    try:
        plan_text = ask_groq(prompt_text, max_tokens=500)
        return plan_text
    except Exception as e:
        return f"[error: expert_planner_skill failed] {e}"

@tool
def robust_search_skill(topic: str, context: Optional[str] = None) -> str:
    """
    Use this skill to generate search queries and gather verified information on a particular topic.
    Optionally provide context like a critique or research plan to focus the search.
    """
    prompt_text = f"{RESEARCH_PLAN_PROMPT}\n\nTask: {topic}"
    if context:
        prompt_text += f"\n\nContext:\n{context}"
    
    try:
        response_text = ask_groq(prompt_text, max_tokens=300)
        queries_data = safe_json_parse(response_text)
        queries = queries_data.get("queries", []) or queries_data.get("text", "").splitlines()
    except Exception as e:
        return f"[error: robust_search_skill failed parsing queries] {e}"

    results = []
    for q in queries:
        try:
            search = tavily.search(query=q, max_results=2)
            results.extend([f"{r.get('content', '')} (Source: {r.get('url', '')})" for r in search.get("results", [])])
        except Exception as e:
            results.append(f"[search_error: {q}] {e}")
            
    return "\n\n".join(results)

@tool
def critique_skill(draft: str) -> str:
    """
    Use this skill to analyze a draft for weaknesses, factual accuracy, and logical cohesion.
    Returns highly critical feedback as JSON data.
    """
    prompt_text = f"{REFLECTION_PROMPT}\n\nDraft:\n{draft}"
    try:
        return ask_groq(prompt_text, max_tokens=500)
    except Exception as e:
        return f"[error: critique_skill failed] {e}"

@tool
def report_writer_skill(topic: str, plan: str, gathered_content: str) -> str:
    """
    Use this skill to piece together the final generated report combining the topic, outline plan, and gathered information content.
    """
    prompt_text = WRITER_PROMPT.format(content=gathered_content) + f"\n\nTask: {topic}\n\nPlan:\n{plan}"
    try:
        return ask_groq(prompt_text, max_tokens=1500)
    except Exception as e:
        return f"[error: report_writer_skill failed] {e}"
