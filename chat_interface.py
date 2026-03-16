# chat_interface.py
import gradio as gr
import uuid
import time
from markdown_pdf import MarkdownPdf, Section

# CSS to handle simple tooltips on citations 
css = """
body {
    background-color: #f7fafc;
}
.tooltip {
  position: relative;
  display: inline-block;
  border-bottom: 2px solid #2b6cb0; 
  cursor: help;
}

.tooltip .tooltiptext {
  visibility: hidden;
  width: 200px;
  background-color: #1a202c;
  color: #e2e8f0;
  text-align: center;
  border-radius: 6px;
  padding: 8px;
  position: absolute;
  z-index: 100;
  bottom: 125%;
  left: 50%;
  margin-left: -100px;
  opacity: 0;
  transition: opacity 0.3s;
  box-shadow: 0px 4px 6px rgba(0,0,0,0.1);
}

.tooltip:hover .tooltiptext {
  visibility: visible;
  opacity: 1;
}
"""

theme = gr.themes.Base(
    primary_hue="slate",
    secondary_hue="gray",
    neutral_hue="slate",
).set(
    body_background_fill="*neutral_50",
    button_primary_background_fill="*primary_700",
    button_primary_background_fill_hover="*primary_600",
    button_primary_text_color="white",
)
with gr.Blocks() as demo:
    gr.Markdown("## 📊 Multi-Agent Strategy Consultant")
    
    # Store the active thread ID
    current_thread = gr.State(str(uuid.uuid4()))
    
    with gr.Row():
        # Sidebar for History
        with gr.Column(scale=1, min_width=200):
            gr.Markdown("### 🕒 Report History")
            history_list = gr.Radio(choices=[], label="Past Sessions", interactive=True)
            refresh_btn = gr.Button("🔄 Refresh History")
            new_chat_btn = gr.Button("📝 New Report")
            
        # Main Chat Area
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=600, elem_classes="tooltip")
            with gr.Row():
                txt = gr.Textbox(placeholder="Type a report topic or question and press Enter", show_label=False, scale=4)
                send_btn = gr.Button("Send", variant="primary", scale=1)
            
            with gr.Row():
                export_btn = gr.Button("📄 Export Last Report to PDF")
                download_file = gr.File(label="Download PDF", visible=False)
    
    gr.Markdown("Logs printed in the server console. If the workflow takes long, wait a few seconds.")

    # --- Callbacks ---
    
    def load_history():
        """Fetch distinct thread IDs from Postgres to populate the sidebar."""
        from db_manager import fetch_thread_history
        threads = fetch_thread_history()
        return gr.update(choices=threads, value=None)

    def start_new_chat():
        """Reset the chat window and generate a new thread ID."""
        return [], str(uuid.uuid4()), None

    def switch_thread(selected_thread):
        """Switch the active thread ID. Future requests map to this session."""
        if not selected_thread:
            return gr.update()
        return selected_thread

    def chat_with_agents_with_thread(message: str, chat_history, thread_id: str):
        if not message:
            return chat_history or []
        if chat_history is None:
            chat_history = []

        chat_history.append({"role": "user", "content": message})
        yield chat_history
        
        # Connect to postgres and stream
        from db_manager import get_postgres_saver
        from app import build_workflow
        
        try:
            with get_postgres_saver() as checkpointer:
                graph = build_workflow(checkpointer)
                
                tid = thread_id or str(uuid.uuid4())
                # Enforce loop limits (recursion_limit) to avoid infinite cycles
                config = {"configurable": {"thread_id": tid}, "recursion_limit": 25}
                initial_input = {"messages": [("user", message)]}
                
                # Create a placeholder in the chat history for the agent's response
                chat_history.append({"role": "assistant", "content": "⏳ Thinking..."})
                yield chat_history
                
                final_text = ""
                # Stream both tool calls and agent messages
                for event in graph.stream(initial_input, config, stream_mode="values"):
                    if "messages" in event:
                        msg = event["messages"][-1]
                        
                        # We intercept tool calls to show step logs
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_name = tc.get("name", "tool")
                                status_msg = f"*(⏳ Using skill: `{tool_name}`)*\n\n"
                                chat_history[-1]["content"] = status_msg
                                yield chat_history
                        
                        # We accumulate AI text content
                        elif msg.type == "ai" and msg.content:
                            final_text = msg.content
                            chat_history[-1]["content"] = final_text
                            yield chat_history
                            
                # Final polish when done streaming
                if not final_text:
                    chat_history[-1]["content"] = "✅ Process finished."
                yield chat_history
                
        except Exception as e:
            error_msg = str(e)
            if "recursion_limit" in error_msg.lower():
                gr.Warning("Workflow exceeded maximum steps. Terminated early.")
                chat_history[-1]["content"] = "⚠️ The agent took too long and the workflow was stopped to prevent an infinite loop."
            else:
                gr.Warning("An unexpected error occurred.")
                chat_history[-1]["content"] = f"❌ Error: {error_msg}"
            yield chat_history

    def export_to_pdf(chat_history):
        """Converts the last AI message from the chat history into a downloadable PDF."""
        if not chat_history:
            return gr.update(visible=False)
            
        # Find the last message from the 'Agents'
        last_agent_msg = ""
        for msg in reversed(chat_history):
            role = msg.get("role", "")
            text = msg.get("content", "")
            if role == "assistant" and not text.startswith("*(⏳"):
                last_agent_msg = text
                break
                
        if not last_agent_msg:
            return gr.update(visible=False)
            
        # Convert Markdown to PDF
        pdf = MarkdownPdf()
        pdf.add_section(Section(last_agent_msg))
        
        output_path = "exported_report.pdf"
        pdf.save(output_path)
        
        return gr.update(value=output_path, visible=True)

    # --- Events ---
    demo.load(load_history, inputs=[], outputs=[history_list])
    refresh_btn.click(load_history, inputs=[], outputs=[history_list])
    
    new_chat_btn.click(start_new_chat, inputs=[], outputs=[chatbot, current_thread, history_list])
    history_list.change(switch_thread, inputs=[history_list], outputs=[current_thread])
    
    txt.submit(chat_with_agents_with_thread, inputs=[txt, chatbot, current_thread], outputs=[chatbot])
    send_btn.click(chat_with_agents_with_thread, inputs=[txt, chatbot, current_thread], outputs=[chatbot])
    export_btn.click(export_to_pdf, inputs=[chatbot], outputs=[download_file])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7861, share=False, theme=theme, css=css)
