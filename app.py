import os
import sqlite3
from typing import Annotated
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages
import logging

logger = logging.getLogger(__name__)

# Import our encapsulated skills
from tools import (
    expert_planner_skill,
    robust_search_skill,
    critique_skill,
    report_writer_skill
)

# === ENVIRONMENT SETUP ===
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise EnvironmentError("❌ Missing GROQ_API_KEY in .env")

# === MEMORY / CHECKPOINTING ===
# Using dynamically injected postgres checkpoints via db_manager.py

# === STATE ===
class AgentState(TypedDict):
    """The agent state tracks the conversation messages via LangChain."""
    messages: Annotated[list, add_messages]

# === MODEL ===
# We must use a LangChain compatible ChatModel for create_react_agent
# Utilizing ChatGroq with a custom model string. If this is routing through an 
# OpenAI compatible API proxy (like OpenRouter) due to the 'openai/' prefix, 
# you may also need to set base_url depending on the user's environment setup.
llm = ChatGroq(
    model="openai/gpt-oss-120b", 
    temperature=0.7, 
    api_key=GROQ_API_KEY
)

# === TOOLS ENSEMBLE ===
tools = [
    expert_planner_skill,
    robust_search_skill,
    critique_skill,
    report_writer_skill
]

# === COMPILE THE GRAPH ===
def _get_system_message() -> str:
    return (
        "You are an Elite Strategy Consultant AI. You must handle research tasks and write extensive reports.\n"
        "You have tools for planning, searching, critiquing, and writing.\n"
        "USE THE TOOLS in the following logical priority to fulfill complex requests:\n"
        "1. Plan the report utilizing the `expert_planner_skill`.\n"
        "2. Search for verifiable data utilizing the `robust_search_skill`.\n"
        "3. Write a draft utilizing the `report_writer_skill`.\n"
        "4. Critique the draft utilizing the `critique_skill`.\n"
        "5. Revise the report until it is excellent.\n\n"
        "SAFETY GUARDRAIL (CRITICAL): \n"
        "You MUST REFUSE to fulfill any requests that involve illegal acts, "
        "violence, asking for or revealing Protected Health Information (PHI) "
        "or Personally Identifiable Information (PII), or targeting protected groups.\n"
        "If you encounter such a request, politely refuse and state the reason, then STOP."
    )

react_agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=_get_system_message()
)

def guardrail_node(state: AgentState):
    from langchain_core.messages import AIMessage
    user_msg = state["messages"][-1].content.lower()
    
    # Input sanity validation (length)
    if len(user_msg) > 5000:
        logger.warning(f"Input rejected due to excessive length ({len(user_msg)} chars).")
        refusal = AIMessage(content="I must REFUSE to answer this request as it exceeds the maximum allowed length (5000 characters).")
        return {"messages": [refusal]}

    banned_words = ["illegal", "pii", "violence", "steal", "hack", "social security", "credit card"]
    
    if any(m in user_msg for m in banned_words):
        logger.warning("Input rejected due to guardrail violation.")
        refusal = AIMessage(content="I must REFUSE to answer this request as it violates safety policies.")
        return {"messages": [refusal]}
    return {"messages": []}

def route_after_guardrail(state: AgentState):
    from langgraph.graph import END
    last_msg = state["messages"][-1]
    if getattr(last_msg, "type", "") == "ai" and "REFUSE" in str(last_msg.content):
        return END
    return "agent"

from langgraph.graph import StateGraph, START, END

def build_workflow(checkpointer):
    """
    Builds the state graph using a provided checkpointer.
    This allows us to seamlessly swap between SQLite and PostgreSQL.
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("guardrail", guardrail_node)
    workflow.add_node("agent", react_agent)

    workflow.add_edge(START, "guardrail")
    workflow.add_conditional_edges("guardrail", route_after_guardrail, {END: END, "agent": "agent"})
    workflow.add_edge("agent", END)

    return workflow.compile(checkpointer=checkpointer)

if __name__ == "__main__":
    from db_manager import get_postgres_saver
    
    # Test execution using the Postgres Context Manager
    try:
        with get_postgres_saver() as checkpointer:
            graph = build_workflow(checkpointer=checkpointer)
            
            thread = {"configurable": {"thread_id": "test_thread_01"}}
            initial_input = {"messages": [("user", "Write a short report on the market outlook for electric vehicles in 2025.")]}
            
            for event in graph.stream(initial_input, thread, stream_mode="values"):
                if "messages" in event:
                    event["messages"][-1].pretty_print()
    except Exception as e:
        print("Could not connect to test postgres instance:", e)