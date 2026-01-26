🚀 EchoText AI
A full-stack AI application that transforms raw text, audio, and video into professional study materials in seconds. Built with Python, Streamlit, and Hugging Face.

🔗 Live Demo: Click here to use the App

📖 About The Project
Studying from long lectures or messy notes is difficult, especially for students. This tool uses Generative AI to take raw content (transcribed audio or pasted text) and transforms it into structured, high-quality study aids.

Key Features:

✨ AI-Powered Study Aids: Uses Meta Llama 3 to generate detailed notes, quizzes, flashcards, and bullet points.

🎙️ Audio Transcription: Integrated with OpenAI Whisper to transcribe MP3, MP4, and WAV files automatically.

📚 History & Profiles: Securely save your generated materials to a personal dashboard powered by Supabase.

🔒 Secure: Authentication handled with hashed passwords and API keys managed via Streamlit Secrets.

🛠️ Tech Stack

Frontend: Streamlit 

LLM (Brain): Hugging Face API (meta-llama/Meta-Llama-3-8B-Instruct)


Transcription: OpenAI Whisper 


Database: Supabase 


Audio Processing: FFmpeg 

💻 How to Run Locally
Follow these steps to run the project on your own computer.

1. Clone the Repository
Bash
git clone https://github.com/jaya-prakash-grahacharya/EchoText_AI.git
cd EchoText_AI
2. Set Up Environment Variables
Create a .streamlit/secrets.toml file (which is ignored by Git ) and add your credentials:

Ini, TOML
SUPABASE_URL = "your_supabase_url"
SUPABASE_API_KEY = "your_supabase_key"
HF_API_KEY = "your_huggingface_token"
3. Install Dependencies
Bash
pip install -r requirements.txt

Note: Ensure ffmpeg is installed on your system path.

4. Run the Application
Bash
streamlit run main.py
