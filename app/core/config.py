from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = APP_DIR.parent

UPLOAD_DIR = PROJECT_DIR / "uploads"
OUTPUT_DIR = PROJECT_DIR / "outputs"

STATIC_DIR = APP_DIR / "static"

ALLOWED_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a"
}