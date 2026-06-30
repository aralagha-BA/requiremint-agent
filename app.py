"""
Minimal Streamlit front-end for the demo / Project Link.

Two phases:
  1. Chat with the Elicitation Agent (free-form interview).
  2. Click "Build Backlog" to run synthesis -> story writing -> critic,
     and display the resulting epics/stories. If the critic raises
     clarifications, they're shown so you can keep chatting before
     rebuilding.

Run with:  streamlit run app.py
"""

import streamlit as st
from orchestrator import RequirementsOrchestrator

st.set_page_config(page_title="Requirements Elicitation Agent", layout="wide")
st.title("🧑‍💼 Requirements Elicitation Agent")
st.caption(
    "Talk through what you need, then generate INVEST-style epics & user stories."
)

if "orchestrator" not in st.session_state:
    st.session_state.orchestrator = RequirementsOrchestrator()
if "messages" not in st.session_state:
    st.session_state.messages = []

orch: RequirementsOrchestrator = st.session_state.orchestrator

# --- Chat panel -------------------------------------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if user_input := st.chat_input("Describe what you need..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    # Basic input hygiene before it ever reaches the agent/tools.
    safe_input = user_input.strip()[:4000]  # cap length, defensive trim

    reply = orch.interview_turn(safe_input)
    st.session_state.messages.append({"role": "assistant", "content": reply})
    with st.chat_message("assistant"):
        st.write(reply)

st.divider()

# --- Backlog generation -------------------------------------------------
if st.button("🛠️ Build Backlog from Conversation", type="primary"):
    with st.spinner("Synthesizing epics, writing stories, running QA review..."):
        session = orch.build_backlog()

    if session.status == "needs_clarification":
        st.warning("The Critic agent flagged open questions before this is final:")
        for q in session.pending_clarifications:
            st.write(f"- {q}")
        st.info("Answer these in the chat above, then click Build Backlog again.")
    else:
        st.success("Backlog ready ✅")

    for epic in session.epics:
        with st.expander(f"📦 {epic.id} — {epic.title}", expanded=True):
            st.write(epic.summary)
            if epic.conflicts:
                st.error("⚠️ Stakeholder conflicts:\n" + "\n".join(epic.conflicts))
            for story in epic.stories:
                st.markdown(
                    f"**{story.id}** — As a *{story.role}*, I want "
                    f"*{story.goal}*, so that *{story.benefit}*  \n"
                    f"Priority: `{story.priority.value}`"
                )
                if story.acceptance_criteria:
                    st.write("Acceptance criteria:")
                    for ac in story.acceptance_criteria:
                        st.write(f"  - {ac}")
                if story.open_questions:
                    st.write("Open questions:")
                    for q in story.open_questions:
                        st.write(f"  - ❓ {q}")

    st.download_button(
        "⬇️ Export backlog as JSON",
        data=str(orch.export()),
        file_name="backlog.json",
    )
