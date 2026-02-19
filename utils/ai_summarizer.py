# ---------- ai_summarizer.py ----------
import re
import os
import logging
import requests

logger = logging.getLogger(__name__)

API_URL = "https://router.huggingface.co/v1/chat/completions"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"

PROMPTS = {
    "notes": (
        "Convert the following lecture into detailed, complete study notes. "
        "Write full paragraphs. Do not summarize. Do not truncate.\n\n"
    ),
    "quiz": (
        "Create real-world quiz questions based on the text.\n"
        "Rules:\n"
        "- Ask clear questions like in exams\n"
        "- Answers must directly answer the question\n"
        "- Do NOT repeat the same sentence\n"
        "Format strictly as:\n"
        "Q: <question>\nA: <answer>\n\n"
    ),
    "flashcards": (
        "Create study flashcards.\n"
        "Rules:\n"
        "- Front = short concept title (2–6 words)\n"
        "- Back = clear explanation\n"
        "- No pronouns, no 'Explain', no notes\n"
        "Format strictly as:\n"
        "Front: <concept>\nBack: <explanation>\n\n"
    ),
    "bullets": "Summarize the following lecture into bullet points:\n\n",
}

def clean_quiz(output: str) -> str:
    """Fixed: Removed backslashes from f-string expressions"""
    blocks = re.split(r"\n\s*\n", output.strip())
    cleaned = []
    for block in blocks:
        q_match = re.search(r"Q:\s*(.+)", block)
        a_match = re.search(r"A:\s*(.+)", block)
        if q_match and a_match:
            # Assign to variables first to avoid backslashes in f-string {}
            q_text = q_match.group(1).strip()
            a_text = a_match.group(1).strip()
            cleaned.append(f"Q: {q_text}\nA: {a_text}")
    return "\n\n".join(cleaned) if cleaned else output

def clean_flashcards(output: str) -> str:
    """Fixed: Cleaned up logic to avoid f-string syntax errors"""
    blocks = re.split(r"\n\s*\n", output.strip())
    cards = []
    for block in blocks:
        f_match = re.search(r"Front:\s*(.+)", block)
        b_match = re.search(r"Back:\s*(.+)", block)
        if f_match and b_match:
            front = f_match.group(1).strip()
            back = b_match.group(1).strip()
            if len(front.split()) <= 6:
                cards.append(f"Front: {front}\nBack: {back}")
    return "\n\n".join(cards) if cards else output

def generate_output(text, output_type="notes"):
    if not text or not text.strip():
        return "No input text provided."

    # Fetch token INSIDE function so load_dotenv() from app.py has time to work
    token = os.getenv("HF_API_KEY")
    prompt = PROMPTS.get(output_type, PROMPTS["notes"]) + text

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "system", "content": "Assistant"}, {"role": "user", "content": prompt}],
        "temperature": 0.4,
    }

    try:
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        result = response.json()["choices"][0]["message"]["content"].strip()

        if output_type == "quiz": return clean_quiz(result)
        if output_type == "flashcards": return clean_flashcards(result)
        return result
    except Exception as e:
        logger.error(f"HF API failed: {e}")
        return f"Error processing request: {text[:100]}..." # Simple fallback