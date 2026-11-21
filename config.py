"""Central configuration. Secrets come from the environment / .env file only."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- Models (override in .env if Google retires one) -------------------------
CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-3.5-flash")
EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
LLM_TEMPERATURE = 0.2

# --- Vector store ------------------------------------------------------------
CHROMA_DIR = os.getenv("CHROMA_DB_DIR", str(BASE_DIR / "chroma_db"))
COLLECTION_NAME = "company_policies"

# --- Chunking / retrieval ----------------------------------------------------
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
TOP_K = 5                    # chunks sent to Gemini with every question
EMBED_BATCH_SIZE = 20        # chunks embedded per API call (gentle on rate limits)

# --- Chat --------------------------------------------------------------------
MAX_QUESTION_CHARS = 1000
HISTORY_MESSAGES = 6         # last 3 exchanges are given to the LLM for follow-ups

SAMPLE_DIR = BASE_DIR / "data" / "sample_policies"


def get_api_key() -> str:
    """Read the key at call time so it is never stored in code or logged."""
    key = os.getenv("GOOGLE_API_KEY", "").strip()
    if key.lower() in {"", "your_gemini_api_key_here"}:
        return ""
    return key
