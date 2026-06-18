import streamlit as st

def render_login_wall():
    if st.session_state.get("user_id") is not None:
        return True

    st.title("🏋️ AI Real-time GYM Trainer")
    st.markdown("A Step to being fit!!")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input(
            "NAME:",
            placeholder="unique name e.g. riddhima"
        )

        submit_button = st.form_submit_button("Start Session")

        if submit_button:
            if not username.strip():
                st.error("Name cannot be empty.")
                return False

            st.session_state["username"] = username
            st.session_state["user_id"] = "1"

            st.rerun()   # rerun after setting session state

    return False