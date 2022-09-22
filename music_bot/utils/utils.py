from typing import List, Union
from enum import Enum

from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from music_bot.scrap.models import Artist, Song


class HTMLTagClass(Enum):
    PAGE_INDEXES = "pnavifa fxmf"
    ARTISTS = "rwr"
    SONG_COVER = "cntfa"


def last_page_number_extractor(bs: BeautifulSoup) -> int:
    page_indexes_div = bs.find("div", class_=HTMLTagClass.PAGE_INDEXES.value)
    if not page_indexes_div:
        return None
    last_page_url = page_indexes_div.find_all("a")[-1].attrs["href"]
    last_page_number = last_page_url.split("/")[-2]
    return int(last_page_number)


def paginate_list(list_: List, page_size=10) -> List[List]:
    return [list_[i : i + page_size] for i in range(0, len(list_), page_size)]


def create_keyboard_page(
    paginated_objects: List[List[Union[Artist, Song]]], requested_page: int
) -> InlineKeyboardMarkup:
    keyboard_layout = []
    # page count on website starts from 1, while python list indexing starts from 0
    requested_object_page = paginated_objects[requested_page - 1]
    for i in range(0, len(requested_object_page) - 1, 2):
        current, next = requested_object_page[i], requested_object_page[i + 1]
        line = [
            InlineKeyboardButton(current.name, callback_data=current),
            InlineKeyboardButton(next.name, callback_data=next),
        ]
        keyboard_layout.append(line)
    if len(requested_object_page) % 2 != 0:
        last = requested_object_page[-1]
        keyboard_layout.append([InlineKeyboardButton(last.name, callback_data=last)])
    last_page = len(paginated_objects)
    next_page, previous_page = "-->", "<--"
    if requested_page == 1:
        line = [
            InlineKeyboardButton(text="خروج", callback_data="exit"),
            InlineKeyboardButton(
                text=next_page, callback_data=f"page_{requested_page+1}"
            ),
        ]
    elif requested_page == last_page:
        line = [
            InlineKeyboardButton(
                text=previous_page, callback_data=f"page_{requested_page-1}"
            ),
            InlineKeyboardButton(text="خروج", callback_data="exit"),
        ]
    else:
        line = [
            InlineKeyboardButton(
                text=previous_page, callback_data=f"page_{requested_page-1}"
            ),
            InlineKeyboardButton(text="خروج", callback_data="exit"),
            InlineKeyboardButton(
                text=next_page, callback_data=f"page_{requested_page+1}"
            ),
        ]
    keyboard_layout.append(line)
    return InlineKeyboardMarkup(keyboard_layout)
