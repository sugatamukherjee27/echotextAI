import re
import os
import logging
import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------- Hugging Face API ----------
API_URL = "https://router.huggingface.co/v1/chat/completions"
token = os.getenv("HF_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
}

MODEL_NAME = "meta-llama/Meta-Llama-3-8B-Instruct"

# ---------- Prompt templates ----------
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

# ---------- CLEANERS (NOT GENERATORS) ----------
def clean_quiz(output: str) -> str:
    blocks = re.split(r"\n\s*\n", output.strip())
    cleaned = []

    for block in blocks:
        q = re.search(r"Q:\s*(.+)", block)
        a = re.search(r"A:\s*(.+)", block)
        if q and a:
            cleaned.append(
                f"Q: {q.group(1).strip()}\nA: {a.group(1).strip()}"
            )

    return "\n\n".join(cleaned) if cleaned else output


def clean_flashcards(output: str) -> str:
    blocks = re.split(r"\n\s*\n", output.strip())
    cards = []

    for block in blocks:
        f = re.search(r"Front:\s*(.+)", block)
        b = re.search(r"Back:\s*(.+)", block)

        if not f or not b:
            continue

        front = f.group(1).strip()
        back = b.group(1).strip()

        if len(front.split()) > 6:
            continue
        if front.lower().startswith(("it", "this", "however", "explain", "note")):
            continue

        cards.append(f"Front: {front}\nBack: {back}")

    return "\n\n".join(cards) if cards else output


# ---------- LOCAL FALLBACKS (ONLY IF HF FAILS) ----------
def _local_quiz(text, qcount=5):
    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+", text)
        if len(s.split()) > 8
    ]

    out = []
    for s in sentences[:qcount]:
        out.append(
            f"Q: What does the following concept explain?\n"
            f"A: {s}"
        )

    return "\n\n".join(out) if out else "No quiz could be generated."


def _local_flashcards(text, count=8):
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cards = []

    for s in sentences:
        if len(s.split()) < 8:
            continue
        if s.lower().startswith(("it ", "this ", "however", "note")):
            continue

        title = " ".join(s.split()[:4]).title()
        cards.append(f"Front: {title}\nBack: {s.strip()}")

        if len(cards) >= count:
            break

    return "\n\n".join(cards) if cards else "No flashcards could be generated."


def _local_bullets(text, max_points=8):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return "\n".join(f"- {s}" for s in sentences[:max_points])


# ---------- MAIN FUNCTION ----------
def generate_output(text, output_type="notes"):
    if not text or not text.strip():
        return "No input text provided."

    prompt = PROMPTS.get(output_type, PROMPTS["notes"]) + text

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful educational assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "max_tokens": 2048,
    }

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        response.raise_for_status()

        result = response.json()["choices"][0]["message"]["content"].strip()

        if output_type == "quiz":
            return clean_quiz(result)

        if output_type == "flashcards":
            return clean_flashcards(result)

        return result

    except Exception:
        logger.exception("HF API failed — using local fallback.")

    # ---------- LOCAL FALLBACK ----------
    if output_type == "quiz":
        return _local_quiz(text)

    if output_type == "flashcards":
        return _local_flashcards(text)

    if output_type == "bullets":
        return _local_bullets(text)

    return text
