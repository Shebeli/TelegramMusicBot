from typing import List, BinaryIO
import os
from cachetools import cached, TTLCache

import requests
from bs4 import BeautifulSoup

import settings
from logger import logger
from models import Artist, Song

cache = TTLCache(maxsize=80, ttl=172800)


@cached(cache)
def all_artists() -> List[Artist]:
    bs = BeautifulSoup(
        (requests.get(settings.BASE_URL)).content, 'html.parser')
    artists = bs.find("aside", class_="rwr").find_all('li')
    return [Artist(artist.text, artist.a['href']) for artist in artists]


@cached(cache)
def _artist_bs(artist: str, page: int = 1) -> BeautifulSoup:
    artist = get_artist(artist)
    url = artist.url
    if page == 1:
        response = requests.get(url)
    else:
        response = requests.get(url + f"/page/{page}")
    return BeautifulSoup(response.content, 'html.parser')


@cached(cache)
def get_artist_page_songs(artist: str, page: int = 1) -> List[Song]:
    bs = _artist_bs(artist, page)
    return [Song
            (
                id=song.a.attrs['href'].split("/")[-2],
                name=song.a.attrs['title'].split(
                    "دانلود ").replace("آهنگ", ""),
                url=song.a.attrs['href']
            )
            for song in bs.find_all("article")]  # songs


def validate_artist(artist: str) -> bool:
    return True if artist in all_artists() else False


def download_songs_from_page(artist: str, page: int = 1, save_dir: str = None) -> None:
    if not save_dir:
        save_dir = getattr(settings, "SAVE_DIR", None)
    songs = get_artist_page_songs(artist)
    if save_dir:
        artist_dir = os.path.join(os.abs.path(save_dir), artist)
    else:
        artist_dir = os.path.abspath(artist)  # "/home/user/همایون شجریان/"
    if not os.path.isdir(artist_dir):
        os.makedirs(artist)
    for song in songs:
        _download_music(song.url, artist_dir)


def download_song(song_id=None, download_url=None, save_dir=None, quality=128) -> str:
    if song_id:
        download_url = settings.DOWNLOAD_URL + song_id
    if not download_url:
        raise Exception(
            "Either a song id or download url should be passed as argument")
    bs = BeautifulSoup((requests.get(download_url)).content, 'html.parser')
    link_tags = bs.find("div", class_="bdownloadfa").find_all("a")
    if save_dir:
        file_dir = os.path.abspath(save_dir)
    else:
        file_dir = os.path.abspath('')
    if quality == 320:
        return _download_music(link_tags[0].attrs['href'], os.path.abspath(file_dir))
    elif quality == 128:
        return _download_music(link_tags[1].attrs['href'], os.path.abspath(file_dir))


def download_artist_album(artist: str, save_dir: str = None) -> None:
    bs = _artist_bs(artist)
    last_page_url = bs.find("div", class_="pnavifa fxmf").find_all(
        "a")[-1].attrs['href']
    last_page_num = last_page_url.split('/')[-2]
    for i in range(int(last_page_num)):
        download_songs_from_page(artist, i+1, save_dir)


@cached(cache)
def all_artist_songs(artist: str) -> Artist:
    bs = _artist_bs(artist)
    last_page_url = bs.find("div", class_="pnavifa fxmf").find_all(
        "a")[-1].attrs['href']
    page_numbers = last_page_url.split('/')[-2]
    artist = get_artist(artist)
    for i in range(int(page_numbers)):
        page_songs = get_artist_page_songs(artist.name, i+1)
        for song in page_songs:
            artist.songs.append(song)
    return artist


@cached(cache)
def get_artist(artist: str) -> Artist:
    for artist_ in all_artists():
        if artist_.name == artist:
            return artist
    raise Exception("Given artist name wasn't found")


def _download_music(music_url: str, file_dir: str) -> str:
    file_name = music_url.split('/')[-1].replace("%20", ' ') # /home/user/همایون شجریان/Irane Man.mp3
    file_full_path = os.path.join(file_dir, file_name)
    if not os.path.isfile(file_full_path):
        with open(file_full_path, "wb") as file:
            _download_file(music_url, file)
            logger.info(f"{file_name} downloaded.")
            return file_full_path
    # sometimes request for downloads throws a broken exception & connection error  and the file stays empty.
    if os.path.getsize(file_full_path) == 0:
        logger.info(f"{file_name} is empty, redownloading.")
        with open(file_full_path, "wb") as file:
            _download_file(music_url, file)
            logger.info(f"{file_name}, Downloaded.")
            return file_full_path
    logger.info(f"{file_name} is already downloaded, skipping.")
    return file_full_path


def _download_file(url: str, file: BinaryIO) -> None:
    with requests.get(url) as response:
        downloaded_file = response.content
        file.write(downloaded_file)


# Music scraper:
#   Check for redundent files so it won't download them again ✅
#   write the download song function for a specific song with audio quality choice ✅
#   download all published songs from an artist can be done in two ways:
#       1- using download songs from page function,
#          can download song from each page very effienctly but limited to song cover quality ✅
#       2- using download song from a url function, more elegant approach and able to select quality
#          but it requires more processing
#   Refactor✅
#
# GUI:
#   ?
#
# Telegram Bot:
#   1- Cache artist lists and their song list to speed up the process ✅
#   2- Remove song and artist name from songs title
#   3- Handle errors for downloading, timeout for uploading, so the bot doesnt stop
#   4- download full album?
#   5- Display the percentage of download or upload process in chat
#   6- There are some exceptions in download links, for eg theres two download pages that have two songs in them and
#       they have different html layout for scraping the song link.
#       https://music-fa.com/download-song/25222/
#       https://music-fa.com/download-song/50071/
#   7- Whenever a music is getting downloaded or uploaded by server, it should inform the user about the process which should
#       be based on if its cached or not.
#   8- Incase user starts a conversation and the conversation is not finished(for eg user deletes the chat with bot),
#        the user cannot continue the conversation.
#       so the conversation should either end compleletly or another conversation replaces  the old one if they type /start
#   9- Possible a return button to previous route for conversation handler?
#   10- logger doesnt log data into file
#   11- some songs still have other artists
# https://music-fa.com/artist/%d9%87%d9%85%d8%a7%db%8c%d9%88%d9%86-%d8%b4%d8%ac%d8%b1%db%8c%d8%a7%d9%86/page/3/
