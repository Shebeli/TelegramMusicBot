import os
from typing import Dict, List, BinaryIO, Literal, Optional
from urllib import response
from cachetools import TTLCache
import asyncio


import requests
from aiohttp import ClientSession
from bs4 import BeautifulSoup

import music_bot.settings as settings
from music_bot.logger import logger
from music_bot.scrap.models import Artist, Song
from music_bot.scrap.decorators import music_cacher
from music_bot.utils.aioutils import fetch
from music_bot.utils.utils import HTMLTagClass, last_page_number_extractor

cache = TTLCache(maxsize=80, ttl=172800)


@music_cacher(cache)
async def get_all_artists() -> List[Artist]:
    async with ClientSession() as session:
        response = await fetch(session, settings.BASE_URL)
        bs = BeautifulSoup(response, "html.parser")
    artists = bs.find("aside", class_=HTMLTagClass.ARTISTS.value).find_all("li")
    return [Artist(artist.text, artist.a.attrs["href"]) for artist in artists]


async def get_artist(artist: str) -> Artist:
    all_artists = await get_all_artists()
    for arti in all_artists:
        if arti.name == artist:
            return arti
    return None


@music_cacher(cache)
async def _artist_bs(artist: Artist, page: int = 1) -> BeautifulSoup:
    url = artist.url
    async with ClientSession() as session:
        if page == 1:
            response = await fetch(session, url)
        else:
            response = await fetch(session, url=url + f"/page/{page}")
    bs = BeautifulSoup(response, "html.parser")
    return bs


async def get_artist_page_songs(artist: Artist, page: int = 1) -> List[Song]:
    bs = await _artist_bs(artist, page)
    return [
        Song(
            id=song.a.attrs["href"].split("/")[-2],
            name=song.a.attrs["title"].replace("دانلود آهنگ ", ""),
            url=song.a.attrs["href"],
        )
        for song in bs.find_all("article")
    ]


@music_cacher(cache)
async def all_artist_songs_paginated(artist: Artist) -> List[List[Song]]:
    bs = await _artist_bs(artist)
    last_page_number = last_page_number_extractor(bs)
    if not last_page_number:
        page_songs = await get_artist_page_songs(artist)
        return 
    paginated_songs = await asyncio.gather(
        *[get_artist_page_songs(artist, i+1) for i in range(last_page_number)]
    )
    return paginated_songs


async def download_songs_from_page(
    artist: str, page: int = 1, save_dir: str = None
) -> None:
    if not save_dir:
        save_dir = getattr(settings, "SAVE_DIR", None)
    songs = await get_artist_page_songs(artist, page)
    if save_dir:
        artist_dir = os.path.join(os.abs.path(save_dir), artist)
    else:
        artist_dir = os.path.abspath(artist)  # "/home/user/همایون شجریان/"
    if not os.path.isdir(artist_dir):
        os.makedirs(artist)
    for song in songs:
        _download_music(song.url, artist_dir)


async def download_song(
    song: Song,
    save_dir: str = None,
    selected_quality: Literal["320", "128", "any"] = "any",
) -> str:
    music_download_links = await music_link_extractor(song)
    if save_dir:
        file_dir = os.path.abspath(save_dir)
    else:
        file_dir = os.path.abspath("")
    audio_links = []
    for quality_choices in music_download_links.values():
        if selected_quality not in quality_choices or selected_quality == "any":
            audio_links.append(quality_choices.popitem()[1])
        else:
            audio_links.append(quality_choices[selected_quality])
    downloaded_file_paths = [
        _download_music(audio_link, file_dir) for audio_link in audio_links
    ]
    return downloaded_file_paths


async def music_link_extractor(
    song: Song,
) -> Dict[
    str, Dict[Optional[Literal["320", "128", "unknown"]], str]
]:  # unnessacry complex data structure, needs refactoring
    async with ClientSession() as session:
        response_content = await fetch(session, song.url)
    bs = BeautifulSoup(response_content, "html.parser")
    links = [
        a_tag.attrs["href"]
        for a_tag in bs.find("div", class_=HTMLTagClass.SONG_COVER.value).find_all("a")
    ]
    audio_links = set(filter(lambda link: link[-4:] == ".mp3", links))  # no duplicates!
    if not audio_links:
        raise Exception("No audio links were found")
    QUALITY_START_INDEX, QUALITY_END_INDEX = -8, -5
    SONG_NAME_END_INDEX = -10
    songs = dict()
    # audio_link sample: https://ups.music-fa.com/tagdl/6e41/Masih%20-%20Rose%20(320).mp3
    for audio_link in audio_links:
        audio_name = audio_link.split("/")[-1].replace("%20", " ")[:SONG_NAME_END_INDEX]
        song_quality = audio_link[QUALITY_START_INDEX:QUALITY_END_INDEX]
        if audio_name not in songs:
            songs[audio_name] = dict()
        if song_quality not in ("128", "320"):
            songs[audio_name]["unknown_quality"] = audio_link
        songs[audio_name][song_quality] = audio_link
    return songs


async def download_artist_album(artist: str, save_dir: str = None) -> None:
    bs = await _artist_bs(artist)
    last_page_number = last_page_number_extractor(bs)
    for i in range(last_page_number):
        await download_songs_from_page(artist, i + 1, save_dir)


def _download_music(music_url: str, file_dir: str) -> str:
    file_name = music_url.split("/")[-1].replace("%20", " ")
    # /home/user/همایون شجریان/Irane Man.mp3
    file_full_path = os.path.join(file_dir, file_name)
    if not os.path.isfile(file_full_path):
        logger.info(f"{file_name} doesn't exist, downloading.")
        with open(file_full_path, "wb") as file:
            _download_file(music_url, file)
            logger.info(f"{file_name} downloaded.")
        return file_full_path
    # sometimes request for downloads throws a broken exception & connection error and the file stays empty.
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
