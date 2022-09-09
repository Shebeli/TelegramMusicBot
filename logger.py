import logging


file_handler = logging.FileHandler("music_bot.log")
stream_handler = logging.StreamHandler()

formatter = logging.Formatter(
    "%(asctime)s | %(name)s | %(levelname)s | %(message)s")
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger = logging.getLogger("music_bot")
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

logger.setLevel(logging.INFO)
