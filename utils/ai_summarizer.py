import re
import os
import logging
import requests
import streamlit as st

logger = logging.getLogger(__name__)

API_URL = "https://router.huggingface.co/v1/chat/completions"
# Using st.secrets for Streamlit Cloud deployment
token = st.secrets.get("HF_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"

PROMPTS = {
    "notes": (
        "Provide a comprehensive, detailed set of study notes based on the text below. "
        "Expand on concepts and use clear headings. Do not summarize; ensure all technical details are kept.\n\n"
    ),
    "quiz": (
        "Create real-world exam questions based on the text.\n"
        "Format strictly as:\n"
        "Q: <question>\nA: <answer>\n\n"
    ),
    "flashcards": (
        "Create study flashcards for key concepts.\n"
        "Format strictly as:\n"
        "Front: <concept>\nBack: <explanation>\n\n"
    ),
    "bullets": "Summarize the following into concise bullet points for quick review:\n\n",
}

def clean_quiz(output: str) -> str:
    blocks = re.split(r"\n\s*\n", output.strip())
    cleaned = []
    for block in blocks:
        q = re.search(r"Q:\s*(.+)", block)
        a = re.search(r"A:\s*(.+)", block)
        if q and a:
            cleaned.append(f"Q: {q.group(1).strip()}\nA: {a.group(1).strip()}")
    return "\n\n".join(cleaned)

def clean_flashcards(output: str) -> str:
    blocks = re.split(r"\n\s*\n", output.strip())
    cards = []
    for block in blocks:
        f = re.search(r"Front:\s*(.+)", block)
        b = re.search(r"Back:\s*(.+)", block)
        if f and b:
            front = f.group(1).strip()
            if len(front.split()) <= 6:
                cards.append(f"Front: {front}\nBack: {b.group(1).strip()}")
    return "\n\n".join(cards)

def generate_output(text, output_type="notes"):
    if not text or not text.strip():
        return "No input text provided."

    prompt = PROMPTS.get(output_type, PROMPTS["notes"]) + text

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a professional academic assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"].strip()

        if output_type == "quiz":
            cleaned = clean_quiz(result)
            return cleaned if cleaned else result
        
        if output_type == "flashcards":
            cleaned = clean_flashcards(result)
            return cleaned if cleaned else result

        return result

    except Exception as e:
        logger.error(f"API Error: {e}")
        return "The AI service is currently unavailable. Please try again later."