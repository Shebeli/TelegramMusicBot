import logging
from requests import exceptions

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

from settings import TELEGRAM_BOT_TOKEN, SECRET_FILE_PATH, SAVE_DIR
from scrap import download_song, get_artists, validate_artist, all_artist_songs_info


handlers = [logging.FileHandler("musicbot.log"), logging.StreamHandler()]

logging.basicConfig(
    handlers=handlers,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

ARTIST_ROUTE, SONG_ROUTE = range(2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    logger.info(f"User {user.full_name} started the bot")
    keyboard = [
        [
            InlineKeyboardButton("دریافت لیست خوانندگان",
                                 callback_data='artists_page_1'),
            InlineKeyboardButton("لیست آهنگ های خواننده",
                                 callback_data='artist_songs')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "به بات موزیکفا خوش آمدید!\n برای خروج از بات از /exit استفاده بکنید و یا دکمه خروج را فشار دهید \n یک گزینه را انتخاب کنید"
    message = await update.message.reply_text(text, reply_markup=reply_markup)
    context.chat_data['start_message'] = message.message_id
    return ARTIST_ROUTE


async def list_artists(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("در حال دریافت لیست خوانندگان ...")
    artists = get_artists()
    paginated_artists = [artists[i:i+10]
                         for i in range(0, len(artists), 10)]  # need to be cached\
    page = int(query.data.split("_")[-1])  # eg. artists_3
    keyboard = []
    artists = paginated_artists[page-1]
    # 0, 2, 4, 6 [1, 2, 3, 4, 5, 6, 7]
    for i in range(0, int(len(artists)) - 1, 2):
        artist1, artist2 = artists[i], artists[i+1]
        line = [
            InlineKeyboardButton(artist1, callback_data=artist1),
            InlineKeyboardButton(artist2, callback_data=artist2)
        ]
        keyboard.append(line)
    if len(artists) % 2 != 0:
        keyboard.append([
            InlineKeyboardButton(artists[-1], callback_data=artists[-1])
        ])
    if page == 1:
        line = [
            InlineKeyboardButton("خروج", callback_data="exit"),
            InlineKeyboardButton(
                "-->", callback_data=f"artists_page_{page+1}")
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
    return ARTIST_ROUTE


async def input_artist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="نام خواننده خود را وارد کنیم. مثل:\n همایون شجریان",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("خروج", callback_data="exit")]
            ]))
    return ARTIST_ROUTE


async def set_artist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        artist = update.callback_query.data
        update.callback_query = None
    else:
        artist = update.message.text
    logger.info(
        f"Callback query in setting artist func:{update.callback_query}")
    if not validate_artist(artist):
        await update.message.reply_text(
            "خواننده مورد نظر پیدا نشد. لطفا دوباره نام خواننده را وارد نمایید."
        )
        return ARTIST_ROUTE
    context.user_data.update({"requested_artist": artist})
    await list_artist_songs(update, context)
    return SONG_ROUTE


async def list_artist_songs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    artist = context.user_data.get("requested_artist")
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("در حال دریافت لیست آهنگ ها ...")
    else:
        msg_id = context.chat_data.get("start_message")
        await context.bot.edit_message_text(
            text="در حال دریافت لیست آهنگ ها ...",
            chat_id=update.effective_chat.id,
            message_id=msg_id,)
    songs = all_artist_songs_info(artist)  # need to be cached\
    last_page_index = len(songs)
    if query:
        await query.answer()
        page = int(query.data.split("_")[-1])
    else:
        page = 1
    keyboard = []
    songs = songs[page-1]
    for i in range(0, int(len(songs)) - 1, 2):
        song1, song2 = songs[i], songs[i+1]
        line = [
            InlineKeyboardButton(song1.get("title"),
                                 callback_data=song1.get("id")),
            InlineKeyboardButton(song2.get("title"),
                                 callback_data=song2.get("id"))
        ]
        keyboard.append(line)
    if len(songs) % 2 != 0:
        keyboard.append([
            InlineKeyboardButton(
                songs[-1].get("title"), callback_data=songs[-1].get("id"))])
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
        msg_id = context.chat_data.get("start_message")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_id,
            text=f"خواننده انتخاب شده:\n{artist}\nیک آهنگ را انتخاب کنید.",
            reply_markup=reply_markup)
    return SONG_ROUTE


async def download_selected_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_msg = await update.effective_chat.send_message(text="در حال دانلود آهنگ ...")
    logger.info(f"User {update.effective_user.full_name} started the bot")
    try:
        file_path = download_song(query.data, SAVE_DIR)
        logger.info(
            f"User {update.effective_user.full_name} requested song: {file_path.split('/')[-1]}")
    except exceptions.ChunkedEncodingError or exceptions.SSLError:
        await update.effective_chat.send_message("دانلود به مشکل خورد لطفا دوباره سعی کنید!")
        await status_msg.delete()
        return SONG_ROUTE
    await status_msg.edit_text(text="در حال ارسال آهنگ ...")
    file = open(file_path, 'rb')
    await update.effective_chat.send_audio(file, write_timeout=300)
    if not context.user_data.get("download_inform"):
        await status_msg.edit_text(
            text="آهنگ دانلود شد. \n میتوانید از لیست آهنگ هایی که هنوز در لیست بالا موجود هستند آهنگ دانلود کنید در غیر این صورت دکمه خروج را فشار دهید")
        context.user_data['download_inform'] = True
    else:
        await status_msg.delete()
    return SONG_ROUTE


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
        msg_id = context.chat_data.get("start_message")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg_id,
            text="ممنون که از بات موزیکفا استفاده میکنید !")
    return ConversationHandler.END


def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],  # /begin
        states={
            ARTIST_ROUTE: [
                CallbackQueryHandler(
                    list_artists, pattern=r"^artists_page_\d+$"),
                CallbackQueryHandler(input_artist, pattern=r"^artist_songs$"),
                CallbackQueryHandler(
                    set_artist, pattern=r"^[ آابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیئ]+$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, set_artist),
            ],
            SONG_ROUTE: [
                CallbackQueryHandler(
                    list_artist_songs, pattern=r"^songs_\d+$"),
                CallbackQueryHandler(download_selected_song, pattern=r"^\d+$")
            ]
        },
        fallbacks=[
            CallbackQueryHandler(exit, pattern=r"^exit$"),
            CommandHandler("exit", exit, )
        ],
    )
    secret_command = CommandHandler('secret', secret)
    # help = CommandHandler()
    # info = CommandHandler
    application.add_handler(conv_handler)
    application.add_handler(secret_command)
    application.run_polling()


if __name__ == '__main__':
    main()


# SAMPLE KEYBOARD
# [
#         [
#             InlineKeyboardButton("Artist 1", callback_data="Meow"),
#             InlineKeyboardButton("Artist 2 Dogie", callback_data="awoo"),
#             InlineKeyboardButton("Artist 3 Dogie", callback_data="bark"),
#         ],
#         [
#             InlineKeyboardButton("Artist 4", callback_data="3"),
#             InlineKeyboardButton("Artist 5", callback_data="3"),
#             InlineKeyboardButton("Artist 6", callback_data="3")
#         ]
# ]
