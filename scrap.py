from typing import Dict, List, Tuple
import os

import requests
from bs4 import BeautifulSoup

import settings


def validate_artist(artist: str) -> bool:
    return True if artist in get_artists() else False


def get_artist_songs_info(artist: str, page: int = 1) -> List[Dict]:
    bs = _artist_bs(artist, page)
    data = [
        {
            "id": art.a.attrs['href'].split("/")[-2],
            "title": art.a.attrs['title'].split("دانلود ")[-1],
            "url": art.a.attrs['href'],
        }
        for art in bs.find_all("article")]
    return data


def get_artists() -> List[Tuple[str, str]]:
    bs = BeautifulSoup(
        (requests.get(settings.BASE_URL)).content, 'html.parser')
    artists = bs.find("aside", class_="rwr").find_all('li')
    return [artist.text for artist in artists]


def download_songs_from_page(artist: str, page: int = 1, save_dir: str = None) -> None:
    bs = _artist_bs(artist, page)
    arts = bs.find_all("article")  # songs
    if save_dir:
        artist_dir = os.path.join(os.abs.path(save_dir), artist)
    else:
        artist_dir = os.path.abspath(artist)
    if not os.path.isdir(artist_dir):
        os.makedirs(artist)
    for art in arts:
        if art.audio:
            _download_music(art.audio.attrs['src'], artist_dir)


def download_song(song_id, save_dir=None, quality=128) -> os.path.abspath:
    url = settings.DOWNLOAD_URL + song_id
    bs = BeautifulSoup((requests.get(url)).content, 'html.parser')
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
    page_numbers = last_page_url.split('/')[-2]
    for i in range(int(page_numbers)):
        download_songs_from_page(artist, i+1, save_dir)

# songs = [
#   [("Meow Meow Meow", "Cat")],
#   [("Bark Bark Bark", "Dog")]
# ]
#
#


def all_artist_songs_info(artist: str) -> List[List[Dict]]:
    bs = _artist_bs(artist)
    last_page_url = bs.find("div", class_="pnavifa fxmf").find_all(
        "a")[-1].attrs['href']
    page_numbers = last_page_url.split('/')[-2]
    artist_songs = []
    for i in range(int(page_numbers)):
        page_songs = get_artist_songs_info(artist, i+1)
        artist_songs.append(page_songs)
    return artist_songs


def _artist_bs(artist, page=1):
    artist = artist.replace(" ", "-")
    url = f"{settings.ARTIST_URL}/{artist}/"
    if page == 1:
        response = requests.get(url)
    else:
        response = requests.get(url + f"/page/{page}")
    if response.status_code != 200:
        raise Exception("Given artist name is either wrong or not found!")
    return BeautifulSoup(response.content, 'html.parser')


def _download_music(music_url, file_dir):
    file_name = music_url.split('/')[-1].replace("%20", ' ')
    file_full_path = os.path.join(file_dir, file_name)
    if not os.path.isfile(file_full_path):
        file = open(file_full_path, "wb")
        _download_file(music_url, file)
        print(file_name, "Downloaded!")
        return file_full_path
    print(file_name, "is already downloaded, skipping.")
    return file_full_path


def _download_file(url, file):
    downloaded_file = requests.get(url).content
    file.write(downloaded_file)
    file.close()

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
#   1- Cache artist lists and their song list to speed up the   vprocess
#   2- Remove song and artist name from songs title
#   3- Handle errors for downloading, timeout for uploading, so the bot doesnt stop
#   4- download full album?
#   5- Display the percentage of download or upload process in chat


# https://music-fa.com/artist/%d9%87%d9%85%d8%a7%db%8c%d9%88%d9%86-%d8%b4%d8%ac%d8%b1%db%8c%d8%a7%d9%86/page/3/
