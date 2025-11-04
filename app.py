import os
import yaml
import streamlit as st
from datetime import datetime
try:
    from openai import OpenAI
    use_new_sdk = True
except Exception:
    import openai
    use_new_sdk = False

APP_TITLE = "AI Helpdesk Assistant"

def load_kb(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}

def build_prompt(mode, topic, issue_text, kb):
    playbooks = kb.get("playbooks", {})
    topic_notes = playbooks.get(topic, [])
    header = f"You are an experienced data center technician. Mode: {mode}. Topic: {topic}."
    kb_section = "Known good steps for this topic:\n" + "\n".join([f"- {s}" for s in topic_notes]) if topic_notes else "No known steps."
    task = (
        "Return a short numbered checklist for an L1 or L2 technician. "
        "Be specific and safety aware. "
        "If escalation is needed, list exactly what logs, photos, and metrics to collect. "
        "Keep sentences short."
    )
    if mode == "Draft customer reply":
        task = (
            "Write a short professional customer reply. "
            "Acknowledge the issue, list the next steps, request any needed info, and set a basic expectation. "
            "Use plain language."
        )
    return f"""{header}

Issue:
{issue_text}

{kb_section}

Task:
{task}
"""

def call_openai(prompt: str):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return "Set your OPENAI_API_KEY environment variable to run the assistant."
    try:
        if use_new_sdk:
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":"You are a concise, safety focused helpdesk coach."},
                          {"role":"user","content":prompt}],
                temperature=0.3,
            )
            return resp.choices[0].message.content
        else:
            openai.api_key = api_key
            resp = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[{"role":"system","content":"You are a concise, safety focused helpdesk coach."},
                          {"role":"user","content":prompt}],
                temperature=0.3,
            )
            return resp["choices"][0]["message"]["content"]
    except Exception as e:
        return f"OpenAI error: {e}"

def main():
    st.set_page_config(page_title=APP_TITLE, page_icon="🛠️")
    st.title(APP_TITLE)
    st.caption("Troubleshooting steps and customer replies for common issues")

    kb = load_kb("kb.yaml")

    with st.sidebar:
        st.subheader("Settings")
        topic = st.selectbox(
            "Topic",
            ["Server boot", "Networking", "Storage", "GPU rack", "Cabling", "Other"],
            index=0
        )
        mode = st.radio("Mode", ["Troubleshoot checklist", "Draft customer reply"], index=0)
        st.markdown("Use environment variable OPENAI_API_KEY")
        st.markdown("Edit kb.yaml to add playbooks")

    issue_text = st.text_area("Describe the issue", height=160, placeholder="Example: Node does not POST after RAM replacement")
    if st.button("Generate"):
        prompt = build_prompt(mode, topic, issue_text.strip(), kb)
        with st.spinner("Thinking..."):
            output = call_openai(prompt)
        st.markdown("### Result")
        st.write(output)

        # Allow download of the session text
        ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        report = f"# {APP_TITLE}\n\n**Mode:** {mode}\n\n**Topic:** {topic}\n\n**Issue:**\n{issue_text}\n\n**Output:**\n{output}\n"
        st.download_button("Download result as Markdown", report, file_name=f"helpdesk_{ts}.md")

    st.markdown("---")
    st.markdown("Tips: keep the description short, add steps to kb.yaml for better guidance.")

if __name__ == "__main__":
    main()