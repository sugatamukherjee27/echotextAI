import os
import uuid
import logging
import shutil
import streamlit as st
from supabase import create_client, Client
from werkzeug.security import check_password_hash, generate_password_hash

# AI / ML utils
from utils.speech_to_text import convert_to_text
from utils.ai_summarizer import generate_output

hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
st.markdown(hide_style, unsafe_allow_html=True)

# --- INITIAL SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SECURE DATABASE CONNECTION ---
@st.cache_resource
def get_supabase_client() -> Client:
    """Initializes and caches the Supabase client."""
    url = st.secrets.get("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_API_KEY") or os.getenv("SUPABASE_API_KEY")
    
    if not url or not key:
        st.error("Missing Supabase configuration. Please check Streamlit Secrets.")
        st.stop()
    return create_client(url, key)

supabase = get_supabase_client()

# --- AUTHENTICATION & REGISTRATION LOGIC ---
def login_user(username, password):
    try:
        response = supabase.table("users").select("*").eq("username", username).execute()
        user_list = response.data
        if user_list:
            user = user_list[0]
            if check_password_hash(user['password'], password):
                return user
    except Exception as e:
        logger.error(f"Database login error: {e}")
    return None

def register_user(username, email, password):
    try:
        new_id = str(uuid.uuid4())
        hashed_pw = generate_password_hash(password)
        user_data = {
            "id": new_id,
            "username": username,
            "email": email,
            "password": hashed_pw
        }
        supabase.table("users").insert(user_data).execute()
        return True
    except Exception as e:
        st.error(f"Registration error: {e}")
        return False

# --- UI PAGES ---

def auth_page():
    st.title("🚀 EchoText AI")
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["Sign In", "Create Account"])

    with tab1:
        st.subheader("Welcome Back")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit:
                user = login_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid username or password")

    with tab2:
        st.subheader("Join EchoText AI")
        with st.form("reg_form"):
            reg_user = st.text_input("Choose Username")
            reg_email = st.text_input("Email Address")
            reg_pass = st.text_input("Choose Password", type="password")
            reg_submit = st.form_submit_button("Register Now", use_container_width=True)
            
            if reg_submit:
                if reg_user and reg_pass:
                    if register_user(reg_user, reg_email, reg_pass):
                        st.success("Account created! You can now Sign In.")
                    else:
                        st.error("Error: Registration failed (Username might be taken).")
                else:
                    st.warning("Username and Password are required.")

def dashboard_page():
    st.sidebar.title(f"Hello, @{st.session_state.user['username']}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()

    st.header("✨ Generate Study Materials")
    
    output_mode = st.selectbox(
        "What should the AI create?", 
        ["Notes", "Quiz", "Flashcards", "Bullets"]
    )
    
    input_text = st.text_area("Paste text content here...", height=200)
    audio_file = st.file_uploader(
        "Or upload Audio or Video", 
        type=["mp3", "wav", "mp4", "m4a", "flac", "ogg", "webm"]
    )

    if st.button("Start AI Generation", type="primary"):
        if not input_text and not audio_file:
            st.warning("Please provide either text or an audio file.")
            return

        hf_token = st.secrets.get("HF_API_KEY") or os.getenv("HF_API_KEY")
        if not hf_token:
            st.error("Hugging Face API Key is missing!")
            return

        with st.status("AI is processing...", expanded=True) as status:
            final_text = ""
            
            # 1. Handle Audio Transcription
            if audio_file:
                status.write("Processing audio file...")
                unique_id = uuid.uuid4().hex
                temp_path = f"temp_{unique_id}_{audio_file.name}"
                
                try:
                    with open(temp_path, "wb") as f:
                        f.write(audio_file.getbuffer())
                    
                    status.write("Transcribing with Whisper (this may take a minute)...")
                    final_text = convert_to_text(temp_path)
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
            else:
                final_text = input_text
            
            # 2. Handle AI Summarization
            if final_text:
                status.write("Generating AI output...")
                result = generate_output(final_text, output_type=output_mode.lower())
                
                status.update(label="Generation Complete!", state="complete", expanded=False)
                
                st.subheader(f"Results: {output_mode}")
                st.markdown(result)
                
                # 3. Save to History
                try:
                    history_data = {
                        "user_id": st.session_state.user['id'],
                        "input_text": final_text[:500] + ("..." if len(final_text) > 500 else ""),
                        "output_text": result,
                        "type": output_mode.lower()
                    }
                    # Executing the insert
                    supabase.table("history").insert(history_data).execute()
                    st.toast("Saved to your history!")
                except Exception as e:
                    # If this triggers, your RLS policies or column names are likely the cause
                    st.error(f"Failed to save to history: {e}")
                    logger.error(f"History save error: {e}")

def history_page():
    st.title("📚 Study History")
    user_id = st.session_state.user['id']
    try:
        # Fetching records for the logged-in user
        response = supabase.table("history").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
        if response.data:
            for item in response.data:
                type_label = item.get('type', 'Notes').capitalize()
                with st.expander(f"{type_label} - {item.get('created_at', 'Recent')}"):
                    st.write("**Source Preview:**")
                    st.text(item.get('input_text', 'No preview available'))
                    st.divider()
                    st.write(f"**Generated {type_label}:**")
                    st.write(item.get('output_text', 'No content found'))
        else:
            st.info("Your history is empty. Go to the Dashboard to generate something!")
    except Exception as e:
        st.error(f"Could not load history: {e}")

def profile_page():
    st.title("👤 User Profile")
    user = st.session_state.user
    
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(
            f"""<div style="background-color: #EE4B2B; border-radius: 50%; width: 80px; height: 80px; 
            display: flex; align-items: center; justify-content: center; color: white; font-size: 35px;">
            {user['username'][0].upper()}</div>""", unsafe_allow_html=True
        )
    with col2:
        st.write(f"**Username:** @{user['username']}")
        st.write(f"**Email:** {user['email']}")

    st.divider()

    # --- CHANGE PASSWORD ---
    with st.expander("🔐 Change Password"):
        with st.form("change_pw_form"):
            new_pw = st.text_input("New Password", type="password")
            confirm_pw = st.text_input("Confirm New Password", type="password")
            pw_submit = st.form_submit_button("Update Password")
            
            if pw_submit:
                if new_pw == confirm_pw and len(new_pw) >= 6:
                    hashed_pw = generate_password_hash(new_pw)
                    try:
                        supabase.table("users").update({"password": hashed_pw}).eq("id", user['id']).execute()
                        st.success("Password updated successfully!")
                    except Exception as e:
                        st.error(f"Update failed: {e}")
                else:
                    st.error("Passwords must match and be at least 6 characters.")

    # --- DANGER ZONE ---
    with st.expander("⚠️ Danger Zone"):
        st.subheader("Manage Data & Account")
        
        if st.button("Clear All History", use_container_width=True):
            try:
                supabase.table("history").delete().eq("user_id", user['id']).execute()
                st.success("History wiped!")
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing history: {e}")

        st.divider()
        st.error("Delete Account Permanently")
        confirm_delete = st.checkbox("I confirm I want to delete my account and all data.")
        if st.button("DELETE MY ACCOUNT", type="primary", use_container_width=True, disabled=not confirm_delete):
            try:
                # Delete history first (Foreign Key)
                supabase.table("history").delete().eq("user_id", user['id']).execute()
                # Delete user
                supabase.table("users").delete().eq("id", user['id']).execute()
                
                st.session_state.logged_in = False
                st.session_state.user = None
                st.rerun()
            except Exception as e:
                st.error(f"Account deletion failed: {e}")

# --- MAIN NAVIGATION ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    auth_page()
else:
    page = st.sidebar.radio("Menu", ["Dashboard", "History", "Profile"])
    if page == "Dashboard":
        dashboard_page()
    elif page == "History":
        history_page()
    elif page == "Profile":
        profile_page()
