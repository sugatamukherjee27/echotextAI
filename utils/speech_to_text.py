import os
import shutil
import logging
import whisper # This will now point to openai-whisper
import streamlit as st

logger = logging.getLogger(__name__)

@st.cache_resource
def _get_whisper_model(model_name="base"):
    # Ensure FFmpeg is available (Essential for Whisper)
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError("ffmpeg is not installed or not in PATH.")
    
    logger.info(f"Loading Whisper '{model_name}' model...")
    return whisper.load_model(model_name)

def convert_to_text(file_path, model_name="base"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    model = _get_whisper_model(model_name)
    
    # Transcription logic
    result = model.transcribe(
        file_path,
        fp16=False, # Set to False for CPU-based local testing
        language='en' 
    )

    return result["text"].strip()
