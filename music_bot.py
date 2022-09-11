from email import message
import requests


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler
)
from models import Artist, Song

from utils import paginate_list
from settings import TELEGRAM_BOT_TOKEN, SECRET_FILE_PATH, SAVE_DIR
from scrap import download_song, all_artists, get_artist, validate_artist, all_artist_songs_paginated
from logger import logger

ARTIST, SONG, ARTIST_SELECTION = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info(f"User {user.full_name} started the bot")
    keyboard = [
        [
            InlineKeyboardButton("دریافت لیست خوانندگان",
                                 callback_data='artists_page_1'),
            InlineKeyboardButton("لیست آهنگ های خواننده",
                                 callback_data='artist_songs',)
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "به بات موزیکفا خوش آمدید!\n برای خروج از بات از /exit استفاده بکنید و یا دکمه خروج را فشار دهید \n یک گزینه را انتخاب کنید"
    message = await update.message.reply_text(text, reply_markup=reply_markup)
    context.chat_data['start_message'] = message
    return ARTIST


async def list_artists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("در حال دریافت لیست خوانندگان ...")
    artists = all_artists()
    paginated_artists = paginate_list(artists)
    page = int(query.data.split("_")[-1]) 
    keyboard = []
    artists = paginated_artists[page-1]
    for i in range(0, int(len(artists)) - 1, 2):
        line = [
            InlineKeyboardButton(
                artists[i].name, callback_data=artists[i]),
            InlineKeyboardButton(
                artists[i+1].name, callback_data=artists[i+1])
        ]
        keyboard.append(line)
    if len(artists) % 2 != 0:
        keyboard.append([
            InlineKeyboardButton(
                artists[-1].name, callback_data=artists[-1])
        ])
    if page == 1:
        line = [
            InlineKeyboardButton("خروج", callback_data="exit"),
            InlineKeyboardButton(
                "-->", callback_data=f"artists_page_{page+1}"),
        ]
    elif page == len(paginated_artists):
        line = [
            InlineKeyboardButton(
                "<--", callback_data=f"artists_page_{page-1}"),
            InlineKeyboardButton("خروج", callback_data="exit")
        ]
    else:
        line = [
            InlineKeyboardButton(
                "<--", callback_data=f"artists_page_{page-1}"),
            InlineKeyboardButton("خروج", callback_data="exit"),
            InlineKeyboardButton(
                "-->", callback_data=f"artists_page_{page+1}"),
        ]
    keyboard.append(line)
    reply_markup = InlineKeyboardMarkup(keyboard)
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
            [
                [InlineKeyboardButton("خروج", callback_data="exit")]
            ]))
    return ARTIST_SELECTION


async def set_artist_by_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    # await query.answer()
    artist = query.data
    context.user_data.update({"requested_artist": artist})
    update.callback_query = None
    logger.info({f"User {query.from_user.full_name} chose {context.user_data.get('requested_artist')}"})
    await list_artist_songs(update, context)
    return SONG

async def set_artist_by_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    artist = update.message.text
    logger.info(
        f"Callback query in setting artist func:{update.callback_query}")
    if not validate_artist(artist):
        await update.message.reply_text(
            "خواننده مورد نظر پیدا نشد. لطفا دوباره نام خواننده را وارد نمایید."
        )
        return ARTIST_SELECTION
    context.user_data.update({"requested_artist": get_artist(artist)})
    await list_artist_songs(update, context)
    return SONG

async def list_artist_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    artist = context.user_data.get("requested_artist")
    query = update.callback_query
    if query:
        page = int(query.data.split("_")[-1])
        await query.answer()
        # await query.edit_message_text("در حال دریافت لیست آهنگ ها ...")
    else:
        page = 1
        message = context.chat_data.get("start_message")
        await message.edit_text(text="در حال دریافت لیست آهنگ ها ...")
    paginated_songs = all_artist_songs_paginated(artist)
    last_page_index = len(paginated_songs)
    keyboard = []
    page_songs = paginated_songs[page-1]
    for i in range(0, int(len(page_songs)) - 1, 2):
        line = [
            InlineKeyboardButton(page_songs[i].name,
                                 callback_data=page_songs[i]),
            InlineKeyboardButton(page_songs[i+1].name,
                                 callback_data=page_songs[i+1])
        ]
        keyboard.append(line)
    if len(page_songs) % 2 != 0:
        keyboard.append([
            InlineKeyboardButton(
                page_songs[-1].name, callback_data=page_songs[-1])])
    if page == 1:
        line = [
            InlineKeyboardButton("خروج", callback_data="exit"),
            InlineKeyboardButton("-->", callback_data=f"songs_{page+1}")
        ]
    elif page == last_page_index:
        line = [
            InlineKeyboardButton("<--", callback_data=f"songs_{page-1}"),
            InlineKeyboardButton("خروج", callback_data="exit")
        ]
    else:
        line = [
            InlineKeyboardButton("<--", callback_data=f"songs_{page-1}"),
            InlineKeyboardButton("خروج", callback_data="exit"),
            InlineKeyboardButton("-->", callback_data=f"songs_{page+1}"),
        ]

    keyboard.append(line)
    reply_markup = InlineKeyboardMarkup(keyboard)
    if query:
        await query.edit_message_text(
            text="یک آهنگ را انتخاب کنید", reply_markup=reply_markup
        )
    else:
        msg = context.chat_data.get("start_message")
        await msg.edit_text(
            text=f"خواننده انتخاب شده:\n{artist.name}\nیک آهنگ را انتخاب کنید.",
            reply_markup=reply_markup)
    return SONG


async def download_selected_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_msg = await update.effective_chat.send_message(text="در حال دانلود آهنگ ...")
    try:
        song_url = query.data.url
        file_path = download_song(song_url, SAVE_DIR)
        file_name = file_path.split('/')[-1]
        logger.info(f"User {update.effective_user.full_name} downloaded {file_name}")
    except requests.exceptions.ChunkedEncodingError or requests.exceptions.SSLError:
        logger.error(f"User {update.effective_user.full_name} failed to download {file_name}")
        await update.effective_chat.send_message("دانلود به مشکل خورد لطفا دوباره سعی کنید!")
        await status_msg.delete()
        return SONG
    await status_msg.edit_text(text="در حال ارسال آهنگ ...")
    file = open(file_path, 'rb')
    await update.effective_chat.send_audio(file, write_timeout=300)
    if not context.user_data.get("download_inform"):
        await status_msg.edit_text(
            text="آهنگ دانلود شد. \n میتوانید از لیست آهنگ هایی که هنوز در لیست بالا موجود هستند آهنگ دانلود کنید در غیر این صورت دکمه خروج را فشار دهید")
        context.user_data['download_inform'] = True
    else:
        await status_msg.delete()
    return SONG


async def secret(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open(SECRET_FILE_PATH, 'rb')
    )


async def exit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text("ممنون که از بات موزیکفا استفاده میکنید!")
    else:
        message = context.chat_data.get("start_message")
        await message.edit_text("ممنون که از بات موزیکفا استفاده میکنید !")
    return ConversationHandler.END



def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).arbitrary_callback_data(True).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ARTIST: [
                CallbackQueryHandler(set_artist_by_callback,
                                     pattern=Artist),
                CallbackQueryHandler(
                    list_artists, pattern="^artists_page_\d+$"),
                CallbackQueryHandler(input_artist, pattern="^artist_songs$"),
            ],
            ARTIST_SELECTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND,
                               set_artist_by_msg),
            ],
            SONG: [
                CallbackQueryHandler(
                    download_selected_song, pattern=Song),
                CallbackQueryHandler(
                    list_artist_songs, pattern="^songs_\d+$"), #songs_1
            ]
        },
        fallbacks=[
            CallbackQueryHandler(exit, pattern="^exit$"),
            CommandHandler("exit", exit)
        ],
    )
    secret_command = CommandHandler('secret', secret)
    application.add_handler(conv_handler)
    application.add_handler(secret_command)
    application.run_polling()


if __name__ == '__main__':
    main()