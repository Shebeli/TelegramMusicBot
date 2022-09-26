from typing import List
import os

import requests
from telegram import Update, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

from music_bot.scrap.models import Artist, Song
from music_bot.utils.utils import paginate_list, create_keyboard_page
from music_bot.settings import TELEGRAM_BOT_TOKEN, SECRET_FILE_PATH, SAVE_DIR
from music_bot.scrap.scraper import (
    download_song,
    get_all_artists,
    get_artist,
    all_artist_songs_paginated,
    cache,
)
from music_bot.logger import logger

PORT = os.environ.get('PORT')
if PORT:
    port = int(PORT)
ARTIST, SONG, ARTIST_SELECTION = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info(f"User {user.full_name} started the bot")
    keyboard = [
        [
            InlineKeyboardButton(text="دریافت لیست خوانندگان", callback_data="page_1"),
            InlineKeyboardButton(
                text="لیست آهنگ های خواننده",
                callback_data="artist_songs",
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "به بات موزیکفا خوش آمدید!\n برای خروج از بات از /exit استفاده بکنید و یا دکمه خروج را فشار دهید \n یک گزینه را انتخاب کنید"
    message = await update.message.reply_text(text, reply_markup=reply_markup)
    context.user_data["start_message"] = message
    return ARTIST


async def list_artists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    all_artists_cache = cache.get(())
    if not all_artists_cache:
        await query.edit_message_text("در حال دریافت لیست خوانندگان ...")
    artists = await get_all_artists()
    paginated_artists = paginate_list(artists)
    requested_page = int(query.data.split("_")[-1])
    reply_markup = create_keyboard_page(paginated_artists, requested_page)
    await query.edit_message_text(
        text="یک خواننده را انتخاب کنید", reply_markup=reply_markup
    )
    return ARTIST


async def input_artist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="نام خواننده خود را وارد کنیم. مثل:\n همایون شجریان",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(text="خروج", callback_data="exit")]]
        ),
    )
    return ARTIST_SELECTION


async def set_artist_by_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    artist: Artist = query.data
    context.user_data.update({"requested_artist": artist})
    logger.info(
        {
            f"User {query.from_user.full_name} chose {context.user_data.get('requested_artist')} via callback."
        }
    )
    update.callback_query = None  # the reason for this is to not trigger this function's callback query when calling it: list_artist_songs.
    await list_artist_songs(update, context)
    return SONG


async def set_artist_by_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    inputed_artist_name = update.message.text
    artist = await get_artist(inputed_artist_name)
    if not artist:
        await update.message.reply_text(
            "خواننده مورد نظر پیدا نشد. لطفا دوباره نام خواننده را وارد نمایید."
        )
        return ARTIST_SELECTION
    context.user_data.update({"requested_artist": artist})
    logger.info(
        {
            f"User {update.effective_user.full_name} chose {context.user_data.get('requested_artist')} via message input."
        }
    )
    await list_artist_songs(update, context)
    return SONG


async def list_artist_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        requested_page = int(query.data.split("_")[-1]) # query data sample: "page_3"
        await query.answer()
    else:
        requested_page = 1
    artist = context.user_data.get("requested_artist")
    paginated_songs_cache = cache.get((artist.name,))
    start_message = context.user_data.get("start_message")
    if not paginated_songs_cache:
        await start_message.edit_text(text="در حال دریافت لیست آهنگ ها ...")
    paginated_songs = await all_artist_songs_paginated(artist)
    reply_markup = create_keyboard_page(paginated_songs, requested_page)
    await start_message.edit_text(
        text=f"خواننده انتخاب شده:\n{artist.name}\nیک آهنگ را انتخاب کنید.",
        reply_markup=reply_markup,
    )
    return SONG


async def download_selected_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_message = await update.effective_chat.send_message(
        text="در حال دانلود آهنگ ..."
    )
    song: Song = query.data
    try:
        logger.info(f"User {update.effective_user.full_name} requested to download song: {song.name}.")
        file_paths = await download_song(song=song, save_dir=SAVE_DIR)
    except requests.exceptions.ChunkedEncodingError or requests.exceptions.SSLError:
        logger.error(f"User {update.effective_user.full_name} failed to download {song.name}.")
        await update.effective_chat.send_message(
            "دانلود به مشکل خورد لطفا دوباره سعی کنید!"
        )
        await status_message.delete()
        return SONG
    await send_selected_songs(update, context, status_message, file_paths)
    return SONG


async def send_selected_songs(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    status_message: Message,
    file_paths: List[str],
):
    await status_message.edit_text(text="در حال ارسال آهنگ ...")
    for file_path in file_paths:
        with open(file_path, "rb") as file:
            logger.info(
                f"Sending audio: {file_path} to user: {update.effective_user.full_name} "
            )
            await update.effective_chat.send_audio(file, write_timeout=2000)
        logger.info(f"Audio: {file_path} was succesfully sent to user: {update.effective_user.full_name}" )
    if not context.user_data.get("download_inform"):
        await status_message.edit_text(
            text="آهنگ دانلود شد. \n میتوانید از لیست آهنگ هایی که هنوز در لیست بالا موجود هستند آهنگ دانلود کنید در غیر این صورت دکمه خروج را فشار دهید"
        )
        context.user_data["download_inform"] = True
    else:
        await status_message.delete()
    return SONG


async def secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(
        chat_id=update.effective_chat.id, photo=open(SECRET_FILE_PATH, "rb")
    )


async def exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("ممنون که از بات موزیکفا استفاده میکنید!")
    else:
        message = context.chat_data.get("start_message")
        await message.edit_text("ممنون که از بات موزیکفا استفاده میکنید !")
    logger.info(f"User {update.effective_user.full_name} exited the bot.")
    return ConversationHandler.END


def main():
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .read_timeout(500)
        .arbitrary_callback_data(True)
        .build()
    )
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ARTIST: [
                CallbackQueryHandler(set_artist_by_callback, pattern=Artist),
                CallbackQueryHandler(list_artists, pattern="^page_\d+$"),
                CallbackQueryHandler(input_artist, pattern="^artist_songs$"),
            ],
            ARTIST_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_artist_by_msg),
            ],
            SONG: [
                CallbackQueryHandler(download_selected_songs, pattern=Song),
                CallbackQueryHandler(list_artist_songs, pattern="^page_\d+$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(exit, pattern="^exit$"),
            CommandHandler("exit", exit),
        ],
    )
    secret_command = CommandHandler("secret", secret)
    application.add_handler(conv_handler)
    application.add_handler(secret_command)
    if PORT:
        print(PORT)
        application.run_webhook(
            listen="0.0.0.0",
            port=int(PORT),
            url_path=TELEGRAM_BOT_TOKEN,
            webhook_url="https://musicfa-bot.herokuapp.com/" + TELEGRAM_BOT_TOKEN
        )
    else:
        application.run_polling()


if __name__ == "__main__":
    main()
