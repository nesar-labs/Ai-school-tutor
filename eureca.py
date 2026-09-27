import streamlit as st
import os
import requests
import re
from google import genai
from google.genai import types

# --- 1. SECURE API KEY SETUP ---
# Tries to get the key from Streamlit Secrets first, then environment variables, then falls back to hardcoded string for local testing.
api_key = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "MY_API_KEY"))

# --- 2. WEB PAGE CONFIGURATION ---
st.set_page_config(page_title="AI School Tutor", page_icon="🤖", layout="centered")
st.title("Welcome to the AI School Tutor Chat!")

# --- 3. PERSISTENT SESSION STATE INITIALIZATION ---
# This stops Streamlit from resetting your AI connection and chat logs whenever the page refreshes.
if "ai_client" not in st.session_state and api_key and api_key != "MY_API_KEY":
    st.session_state.ai_client = genai.Client(api_key=api_key)
elif "ai_client" not in st.session_state and api_key == "MY_API_KEY":
    # If using the default placeholder string, wait for setup form
    st.session_state.ai_client = None

if "chat" not in st.session_state:
    st.session_state.chat = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "tutor_ready" not in st.session_state:
    st.session_state.tutor_ready = False

# Fallback UI if no key is configured anywhere
if not api_key or api_key == "MY_API_KEY":
    st.warning("🔑 Personal API Key not detected in backend systems.")
    user_provided_key = st.text_input("Please enter your Gemini API Key directly to proceed:", type="password")
    if user_provided_key:
        st.session_state.ai_client = genai.Client(api_key=user_provided_key.strip())
    else:
        st.info("You can also configure this automatically via a `.streamlit/secrets.toml` file.")
        st.stop()

# --- 4. STEP 1: INITIALIZER SETUP FORM ---
if not st.session_state.tutor_ready:
    st.subheader("📚 Enter Class Details to Start")
    
    with st.form("tutor_setup"):
        student_class_input = st.text_input("Enter your class (e.g., Class-8 or 8):", value="Class-8")
        subject_input = st.text_input("Enter your subject (e.g., Science):", value="Science")
        chapter_input = st.text_input("Enter your chapter (e.g., Chapter-1):", value="Chapter-1")
        
        submit_btn = st.form_submit_button("🤖 Initialize AI Tutor Chat Session")
        
    if submit_btn:
        student_class = student_class_input.lower().strip()
        subject = subject_input.lower().strip()
        chapter = chapter_input.lower().strip()

        # Your exact custom dictionary maps for matching input formats
        all_class_inputs = {
            1: ["1", "class-1", "class1", "class 1", "i", "class i", "class-i", "one", "first", "1st"],
            2: ["2", "class-2", "class2", "class 2", "ii", "class ii", "class-ii", "two", "second", "2nd"],
            3: ["3", "class-3", "class3", "class 3", "iii", "class iii", "class-iii", "three", "third", "3rd"],
            4: ["4", "class-4", "class4", "class 4", "iv", "class iv", "class-iv", "four", "fourth", "4th"],
            5: ["5", "class-5", "class5", "class 5", "v", "class v", "class-v", "five", "fifth", "5th"],
            6: ["6", "class-6", "class6", "class 6", "vi", "class vi", "class-vi", "six", "sixth", "6th"],
            7: ["7", "class-7", "class7", "class 7", "vii", "class vii", "class-vii", "seven", "seventh", "7th"],
            8: ["8", "class-8", "class8", "class 8", "viii", "class viii", "class-viii", "eight", "eighth", "8th"],
            9: ["9", "class-9", "class9", "class 9", "ix", "class ix", "class-ix", "nine", "ninth", "9th"],
            10: ["10", "class-10", "class10", "class 10", "x", "class x", "class-x", "ten", "tenth", "10th"]
        }
        
        subject_validation = {
            "Science": ["science", "sci", "general science"],
            "Maths": ["maths", "math", "mathematics", "geometry", "algebra"],
            "English": ["english", "eng", "english literature", "english grammar"],
            "Social-science": ["social science", "sst", "history", "geography", "civics", "social studies"]
        }

        chapter_validation = {
            i: [str(i), f"chapter-{i}", f"chapter{i}", f"chapter {i}", f"ch-{i}", f"ch{i}", f"ch {i}"]
            for i in range(1, 11)
        }

        # Run your evaluation normalization routines
        for class_key, class_checker in all_class_inputs.items():
            if student_class in class_checker:
                student_class = f"Class-{class_key}"
                break

        for subject_name, allowed_inputs in subject_validation.items():
            if subject in allowed_inputs:
                subject = subject_name
                break

        for chapter_num, allowed_inputs in chapter_validation.items():
            if chapter in allowed_inputs:
                chapter = f"Chapter-{chapter_num}"
                break

        # Dynamic cloud repository URL construction
        base_url = f"https://raw.githubusercontent.com/nesar-labs/AI-creation/main/{student_class}/{subject}/{chapter}.pdf"
        
        with st.spinner("🔍 Fetching textbook data from cloud files..."):
            try:
                url_response = requests.get(base_url)
                if url_response.status_code == 200:
                    st.success("🎯 Textbook Chapter Found!")
                    
                    pdf_attachment = types.Part.from_bytes(
                        data=url_response.content,
                        mime_type="application/pdf"
                    )
                    
                    system_instruction = (
                        f"You are an expert school tutor for {student_class} {subject}. "
                        f"You are discussing {chapter} with a student. Use the attached PDF to answer questions. "
                        "Keep answers simple, encouraging, and clear for a school student. "
                        "If they ask something not in the chapter, politely let them know."
                    )
                    
                    # FIX: Utilizing the persistent session client block wrapper instead of a raw global object
                    st.session_state.chat = st.session_state.ai_client.chats.create(
                        model="gemini-3.5-flash-lite",
                        history=[
                            types.Content(
                                role="user", 
                                parts=[
                                    pdf_attachment, 
                                    types.Part.from_text(text="Hi tutor, please analyze this chapter file so I can ask you questions about it.")
                                ]
                            )
                        ],
                        config=types.GenerateContentConfig(
                            system_instruction=system_instruction,
                            temperature=1
                        )
                    )
                    
                    # Update transition states
                    st.session_state.tutor_ready = True
                    st.session_state.messages.append({"role": "assistant", "content": "✨ Chat Started! I have analyzed your chapter. What questions do you have?"})
                    st.rerun()
                else:
                    st.error(f"❌ Failed connection status ({url_response.status_code}). Could not locate your target repository asset path.")
                    st.info(f"Checked path: {base_url}")
            except Exception as e:
                st.error(f"❌ Initialization failure: {str(e)}")

# --- 5. STEP 2: RUNNING INTERACTIVE CHAT VIEW ---
else:
    # Sidebar control options panel
    with st.sidebar:
        st.subheader("⚙️ Session Controls")
        if st.button("Reset & Select New Chapter", type="primary"):
            st.session_state.chat = None
            st.session_state.messages = []
            st.session_state.tutor_ready = False
            st.rerun()

    # Print log elements onto screen layout
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Web text container input collection block 
    if user_msg := st.chat_input("Ask a question about your chapter..."):
        # Append and render user statement instantly 
        st.session_state.messages.append({"role": "user", "content": user_msg})
        with st.chat_message("user"):
            st.markdown(user_msg)

        # Trigger response extraction using persistent chat structures
        with st.chat_message("assistant"):
            with st.spinner("Tutor is writing..."):
                try:
                    response = st.session_state.chat.send_message(user_msg)
                    ai_reply = response.text
                    st.markdown(ai_reply)
                    st.session_state.messages.append({"role": "assistant", "content": ai_reply})
                except Exception as e:
                    st.error(f"❌ Error getting response: {str(e)}")
