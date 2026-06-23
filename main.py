import os
import streamlit as st
from services.auth.login_wall import render_login_wall
from services.state.session_default import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS
from services.Style_loader import load_css, inject_local_font
from services.persistence.exercise_repository import init_db

def main():   
    st.set_page_config(
        page_icon="🏋️",
        page_title="AI Real-time GYM Coach",
        initial_sidebar_state="expanded",
        layout="centered"
    )
    
    # Load custom assets safely
    load_css(os.path.join(os.getcwd(), ".streamlit", "static", "Style.css"))
    inject_local_font(os.path.join(os.getcwd(), ".streamlit", "static", "AdobeClean.otf"), "AdobeClean")

    if not render_login_wall():
        return
        
    initial_session_defaults()
    workout_started = st.session_state.get("workout_started", False)
    
    with st.sidebar:
        st.title("AI Coach")
        if st.session_state.get("username"):
            st.caption(f"👤 Logged in as {st.session_state.username}")
        st.divider()
        
        if not workout_started:
            st.subheader("Workout Plan")
            st.selectbox("Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")
            st.number_input("Sets", min_value=0, max_value=50, key="plan_sets", step=1)
            st.number_input("Reps per Set", min_value=0, max_value=50, key="plan_reps", step=1)
            st.markdown("")
            
            start_session_button = st.button("Start Session", use_container_width=True, key="start_session")
            if start_session_button:
                st.session_state["workout_started"] = True
                st.rerun()
        else:
            exercise = st.session_state.get("plan_exercise")
            
            end_session_button = st.button("End Session", use_container_width=True, key="end_session_button")
            if end_session_button:
                st.session_state["workout_started"] = False
                st.rerun()      
            
            st.markdown("")
            st.subheader("Progress")
            total_reps = st.session_state.get("reps", 0)
            current_set_reps = st.session_state.get("current_set_reps", 0)
            reps_per_set = st.session_state.get("plan_reps", 0)
            sets_completed = st.session_state.get("sets_completed", 0)
            target_sets = st.session_state.get("plan_sets", 0) 
            
            st.metric("Total Reps", f"{total_reps}")
            st.metric("Current Set Reps", f"{current_set_reps} / {reps_per_set}")
            st.metric("Sets Completed", f"{sets_completed} / {target_sets}")
            st.divider()
            
            # Dynamic Exercise Metrics inside Sidebar
            if exercise == "Squats":
                st.subheader("Squat Metrics")
                st.metric("Knee Angle", f"{st.session_state.get('knee_angle', 0)}°")
                st.metric("Back Angle", f"{st.session_state.get('back_angle', 0)}°")
                st.metric("Depth Status", st.session_state.get('depth_status', "Unknown"))
            
            elif exercise == "Push-ups":
                st.subheader("Push-up Metrics")
                st.metric("Elbow Angle", f"{st.session_state.get('elbow_angle', 0)}°")
                st.metric("Body Alignment", st.session_state.get('body_alignment', "Unknown"))
                st.metric("Hip Position", st.session_state.get('hip_status', "Unknown"))

    # --- MAIN PAGE UI SPACE ---
    st.title("AI gym coach")
    st.markdown("Transforming workouts with live posture tracking and smart feedback")
    
    if workout_started:
        st.write("### Live Tracking Feed")
        
        # --- NATIVE STREAMLIT CAMERA INPUT ---
        # This completely replaces the broken webrtc_streamer setup
        img_file_buffer = st.camera_input("Capture Feed", key="native-coach-cam")
        
        if img_file_buffer is not None:
            st.success("Camera frame loaded successfully! Ready for tracking processing.")
    else:
        st.markdown(
            """
            <div style="
                border: 1px dashed #D8E3D2;
                border-radius: 18px;
                padding: 40px 32px;
                text-align: center;
                color: #2F3E34;
                background-color: #F7F5EF;
                margin-top: 32px;
            ">
                <h2 style="color: #8BA888; margin-bottom: 8px;">Make your own workout plan</h2>
                <p style="font-size: 1.05rem;">
                    Choose your exercises and then click <strong>Start Session</strong> 
                    to activate your AI tracking camera coach.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("#### Workout History")

if __name__ == "__main__":
    main()