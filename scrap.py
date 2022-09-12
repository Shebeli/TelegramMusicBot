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
def get_all_artists() -> List[Artist]:
    bs = BeautifulSoup(
        (requests.get(settings.BASE_URL)).content, 'html.parser')
    artists = bs.find("aside", class_="rwr").find_all('li')
    return [Artist(artist.text, artist.a.attrs['href']) for artist in artists]


def _artist_bs(artist: Artist, page: int = 1) -> BeautifulSoup:
    url = artist.url
    if page == 1:
        response = requests.get(url)
    else:
        response = requests.get(url + f"/page/{page}")
    return BeautifulSoup(response.content, 'html.parser')


@cached(cache)
def get_artist(artist: str) -> Artist:
    for arti in get_all_artists():
        if arti.name == artist:
            return arti
    raise Exception("Given artist name wasn't found")


def get_artist_page_songs(artist: Artist, page: int = 1) -> List[Song]:
    bs = _artist_bs(artist, page)
    return [Song
            (
                id=song.a.attrs['href'].split("/")[-2],
                name=song.a.attrs['title'].replace("دانلود آهنگ ", ""),
                url=song.a.attrs['href'],
            )
            for song in bs.find_all("article")]  # songs


def validate_artist(artist: str) -> bool:
    return True if artist in get_all_artists() else False


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


def all_artist_songs_paginated(artist: Artist) -> List[List[Song]]:
    bs = _artist_bs(artist)
    last_page_url = bs.find("div", class_="pnavifa fxmf").find_all(
        "a")[-1].attrs['href']
    page_numbers = last_page_url.split('/')[-2]
    paginated_songs = []
    # the size of pagination is 10 since 10 songs are displayed per page.
    for i in range(int(page_numbers)):
        page_songs = get_artist_page_songs(artist, i+1)
        paginated_songs.append(page_songs)
    return paginated_songs


def _download_music(music_url: str, file_dir: str) -> None:
    file_name = music_url.split('/')[-1].replace("%20", ' ')
    # /home/user/همایون شجریان/Irane Man.mp3
    file_full_path = os.path.join(file_dir, file_name)
    if not os.path.isfile(file_full_path):
        with open(file_full_path, "wb") as file:
            _download_file(music_url, file)
            logger.info(f"{file_name} downloaded.")
    # sometimes request for downloads throws a broken exception & connection error  and the file stays empty.
    if os.path.getsize(file_full_path) == 0:
        logger.info(f"{file_name} is empty, redownloading.")
        with open(file_full_path, "wb") as file:
            _download_file(music_url, file)
            logger.info(f"{file_name}, Downloaded.")
    logger.info(f"{file_name} is already downloaded, skipping.")


def _download_file(url: str, file: BinaryIO) -> None:
    with requests.get(url) as response:
        downloaded_file = response.content
        file.write(downloaded_file)
