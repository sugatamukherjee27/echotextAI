# 🚀 EchoText AI

EchoText AI is a full-stack AI-powered application that transforms raw text, audio, and video into professional study materials in seconds. Built with Python, Streamlit, and Hugging Face, this tool helps students convert messy content into structured, high-quality learning resources.

---

## 🔗 Live Demo
👉 Click here to use the App

https://echotextai-app.streamlit.app/
---

## 📖 About The Project

Studying from long lectures, recorded classes, or unorganized notes can be overwhelming. EchoText AI leverages Generative AI and speech-to-text technology to automatically convert raw input into clear, structured study aids such as notes, quizzes, flashcards, and bullet-point summaries.

The goal is to save time, improve comprehension, and enhance learning efficiency.

---

## ✨ Key Features

- 🤖 **AI-Powered Study Aids**  
  Uses Meta Llama 3 to generate:
  - Detailed notes
  - Quizzes
  - Flashcards
  - Bullet-point summaries

- 🎙️ **Audio & Video Transcription**  
  Integrated with OpenAI Whisper to transcribe:
  - MP3
  - MP4
  - WAV

- 📚 **History & User Profiles**  
  Save and revisit generated materials in a personal dashboard powered by Supabase.

- 🔒 **Secure Authentication**  
  - Hashed passwords  
  - API keys stored using Streamlit Secrets

- ⚡ **Fast & User-Friendly Interface**  
  Built with Streamlit for simplicity and speed.

---

## 🛠️ Tech Stack

- **Frontend:** Streamlit  
- **LLM (Brain):** Hugging Face API (meta-llama/Meta-Llama-3-8B-Instruct)  
- **Transcription:** OpenAI Whisper  
- **Database:** Supabase  
- **Audio Processing:** FFmpeg  
- **Language:** Python

---

## 📂 Project Structure

```
EchoText_AI/
│
├── main.py
├── requirements.txt
├── README.md
├── .streamlit/
│   └── secrets.toml
└── assets/
```

---

## 💻 How To Run Locally

Follow these steps to run EchoText AI on your machine.

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/sugatamukherjee27/EchoTextAI.git
cd EchoText_AI
```

---

### 2️⃣ Create Virtual Environment (Recommended)

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

---

### 3️⃣ Set Up Environment Variables

Create a file:

```
.streamlit/secrets.toml
```

Add your credentials:

```toml
SUPABASE_URL = "your_supabase_url"
SUPABASE_API_KEY = "your_supabase_key"
HF_API_KEY = "your_huggingface_token"
```

---

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

⚠️ Make sure **FFmpeg** is installed and available in your system PATH.

---

### 5️⃣ Run the Application

```bash
streamlit run main.py
```

Open your browser and visit:

```
http://localhost:8501
```

---

## 📸 Screenshots
*(Add screenshots or GIFs here)*

---

## 🔐 Security Notes

- Never commit `.streamlit/secrets.toml`
- Rotate API keys if accidentally exposed
- Use strong passwords

---

## 🚧 Future Improvements

- Support for additional languages
- Export to PDF/Word
- Summarization presets (short/medium/long)
- Collaborative sharing

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository
2. Create a new branch
3. Make your changes
4. Submit a pull request

---

## 📜 License

This project is licensed under the MIT License.

---

## 👨‍💻 Author

**Jaya Prakash Grahacharya**

GitHub: https://github.com/jaya-prakash-grahacharya

---

⭐ If you find this project helpful, please consider giving it a star!

