from email.mime import audio
import os
from typing import List, BinaryIO
from cachetools import cached, TTLCache

import requests
from bs4 import BeautifulSoup

import settings
from logger import logger
from models import Artist, Song
from decorators import music_model_cached

cache = TTLCache(maxsize=80, ttl=172800)


@cached(cache)
def get_all_artists() -> List[Artist]:
    bs = BeautifulSoup((requests.get(settings.BASE_URL)).content, "html.parser")
    artists = bs.find("aside", class_="rwr").find_all("li")
    return [Artist(artist.text, artist.a.attrs["href"]) for artist in artists]


def get_artist(artist: str) -> Artist:
    for arti in get_all_artists():
        if arti.name == artist:
            return arti
    raise Exception("Given artist name wasn't found")


@music_model_cached(cache)
def _artist_bs(artist: Artist, page: int = 1) -> BeautifulSoup:
    url = artist.url
    if page == 1:
        response = requests.get(url)
    else:
        response = requests.get(url + f"/page/{page}")
    bs = BeautifulSoup(response.content, "html.parser")
    return bs


def get_artist_page_songs(artist: Artist, page: int = 1) -> List[Song]:
    bs = _artist_bs(artist, page)
    return [
        Song(
            id=song.a.attrs["href"].split("/")[-2],
            name=song.a.attrs["title"].replace("دانلود آهنگ ", ""),
            url=song.a.attrs["href"],
        )
        for song in bs.find_all("article")
    ]


@music_model_cached(cache)
def all_artist_songs_paginated(artist: Artist) -> List[List[Song]]:
    bs = _artist_bs(artist)
    last_page_url = (
        bs.find("div", class_="pnavifa fxmf").find_all("a")[-1].attrs["href"]
    )
    page_numbers = last_page_url.split("/")[-2]
    paginated_songs = []
    # the size of pagination is 10 since 10 songs are displayed per page.
    for i in range(int(page_numbers)):
        page_songs = get_artist_page_songs(artist, i + 1)
        paginated_songs.append(page_songs)
    return paginated_songs


def validate_artist(artist: str) -> bool:
    return True if artist in get_all_artists() else False


def download_songs_from_page(artist: str, page: int = 1, save_dir: str = None) -> None:
    if not save_dir:
        save_dir = getattr(settings, "SAVE_DIR", None)
    songs = get_artist_page_songs(artist, page)
    if save_dir:
        artist_dir = os.path.join(os.abs.path(save_dir), artist)
    else:
        artist_dir = os.path.abspath(artist)  # "/home/user/همایون شجریان/"
    if not os.path.isdir(artist_dir):
        os.makedirs(artist)
    for song in songs:
        _download_music(song.url, artist_dir)


def download_song(song: Song, save_dir: str = None, quality: int = 128) -> str:
    music_link_extractor
    if save_dir:
        file_dir = os.path.abspath(save_dir)
    else:
        file_dir = os.path.abspath("")
    if quality == 320:
        return _download_music(link_tags[0].attrs["href"], os.path.abspath(file_dir))
    elif quality == 128:
        return _download_music(link_tags[1].attrs["href"], os.path.abspath(file_dir))


def music_link_extractor(song: Song, selected_quality: int) -> bool:
    bs = BeautifulSoup((requests.get(download_url)).content, "html.parser")
    links = [
        a_tag.attrs["href"] for a_tag in bs.find("div", class_="cntfa").find_all("a")
    ]
    audio_links = set(filter(lambda link: link[-4:] == ".mp3", links))  # no duplicates!
    if not audio_links:
        raise Exception("No audio links were found")
    QUALITY_START_INDEX, QUALITY_END_INDEX = -8, -5
    SONG_NAME_END_INDEX = -10
    songs = (
        {}
    )  # link sample: https://ups.music-fa.com/tagdl/6e41/Masih%20-%20Rose%20(320).mp3
    for audio_link in audio_links:
        song_name = audio_link.split("/")[-1].replace("%20", " ")[:SONG_NAME_END_INDEX]
        song_quality = audio_link[QUALITY_START_INDEX:QUALITY_END_INDEX]
        if song_name not in songs:
            songs[song_name] = {}
        if song_quality not in ("128", "320"):
            songs[song_name]["unknown_quality"] = audio_link
        songs[song_name][song_quality] = audio_link


# download audio file based on if the link ends with .mp3
# if there are multiple audio files to download, the process can be breaked down into these steps & constraints
#   if the same audio file exists with different qualities, the selected quality should be filtered
#   if theres more than one unique audio file, it means that the page has multiple songs and each of them
#   should be downloaded seperataly.
#   Therees an exception that even if some download pages have both 320, 120 quality, both links are
#   the same. the only way to get the files quality is through its file name
def download_artist_album(artist: str, save_dir: str = None) -> None:
    bs = _artist_bs(artist)
    last_page_url = (
        bs.find("div", class_="pnavifa fxmf").find_all("a")[-1].attrs["href"]
    )
    last_page_num = last_page_url.split("/")[-2]
    for i in range(int(last_page_num)):
        download_songs_from_page(artist, i + 1, save_dir)


def _download_music(music_url: str, file_dir: str) -> str:
    file_name = music_url.split("/")[-1].replace("%20", " ")
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
    return file_full_path


def _download_file(url: str, file: BinaryIO) -> None:
    with requests.get(url) as response:
        downloaded_file = response.content
        file.write(downloaded_file)
