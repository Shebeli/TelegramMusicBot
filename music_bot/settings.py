import os

PORT = os.environ.get("PORT")
if PORT:
    PORT = int(PORT)
BASE_URL = "https://music-fa.com"
ARTIST_URL = "https://music-fa.com/artist"
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise Exception("No telegram bot token was found in environment variables.")
BASE_DOWNLOAD_URL = "https://music-fa.com/download-song/"
SAVE_DIR = os.path.abspath("downloaded_audios")
if not os.path.exists(SAVE_DIR):
    os.mkdir(SAVE_DIR)
