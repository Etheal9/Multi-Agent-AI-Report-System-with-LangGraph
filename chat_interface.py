# chat_interface.py
import gradio as gr
from copy import deepcopy
import uuid
import time
from app import graph  # your compiled LangGraph graph

# Helper to run the workflow synchronously and return the final draft text.
# Keep this small and predictable.
def run_workflow_for_task(task: str, max_revisions: int = 2, thread_id: str | None = None) -> str:
    """
    Run your graph.sync (stream) and return the last produced draft.
    """
    state = {
        "task": task,
        "plan": "",
        "draft": "",
        "critique": "",
        "content": [],
        "revision_number": 0,
        "max_revisions": max_revisions
    }
    # unique thread id per call (or you can reuse a session-based id)
    tid = thread_id or str(uuid.uuid4())
    thread = {"configurable": {"thread_id": tid}}

    final_draft = ""
    # If your graph.compile used recursion_limit via graph.config earlier, no need here.
    # But pass recursion_limit to be safe (tune as needed)
    try:
        for step in graph.stream(state, thread, recursion_limit=30):
            # Print server-side so you can inspect progress in terminal
            print("GRAPH STEP:", step)
            # step may be like {'generate': {'draft': '...'}}
            # collect latest draft if present
            if isinstance(step, dict):
                # enumerate nested outputs
                for node_out in step.values():
                    if isinstance(node_out, dict) and "draft" in node_out:
                        final_draft = node_out.get("draft") or final_draft
    except Exception as e:
        # return a clear error message in the chat UI
        final_draft = f"[error: workflow failed: {e}]"
        print("Workflow exception:", e)

    return final_draft or "[no draft produced]"

# Gradio callback: accepts (message: str, chat_history: list) and returns updated chat_history
def chat_with_agents(message: str, chat_history):
    if not message:
        return chat_history or []
    if chat_history is None:
        chat_history = []

    # append user's message immediately (so UI shows it)
    chat_history.append(("You", message))

    # run the workflow (blocking). This will print progress to the terminal.
    draft = run_workflow_for_task(message, max_revisions=2)

    # append the agent's reply
    chat_history.append(("Agents", draft))
    return chat_history

# Gradio UI
with gr.Blocks() as demo:
    gr.Markdown("## Multi-Agent AI Report Generator — Chat")
    chatbot = gr.Chatbot()
    with gr.Row():
        txt = gr.Textbox(placeholder="Type a report topic or question and press Enter", show_label=False)
        send_btn = gr.Button("Send")
    # Connect submit and button to the same function.
    txt.submit(chat_with_agents, inputs=[txt, chatbot], outputs=[chatbot])
    send_btn.click(chat_with_agents, inputs=[txt, chatbot], outputs=[chatbot])

    gr.Markdown("Logs printed in the server console. If the workflow takes long, wait a few seconds.")

if __name__ == "__main__":
    # set share=True if you want a temporary public link
    demo.launch(server_name="127.0.0.1", server_port=7860, share=False)
