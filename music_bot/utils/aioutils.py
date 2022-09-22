from aiohttp import ClientSession

from bs4 import BeautifulSoup

from music_bot.scrap.models import Artist
from music_bot.settings import BASE_URL
from music_bot.utils.utils import last_page_number_extractor, HTMLTagClass


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()


# This function is not used in program, but rather in debugging and testing.
async def artist_with_most_pages() -> Artist:
    async with ClientSession() as session:
        response = await fetch(session, BASE_URL)
        bs = BeautifulSoup(response, "html.parser")
        artists = bs.find("aside", class_=HTMLTagClass.ARTISTS.value).find_all("li")
        max_page = 0
        for artist in artists:
            response = await fetch(session, artist.a.attrs["href"])
            art_bs = BeautifulSoup(response, "html.parser")
            last_page_number = last_page_number_extractor(art_bs)
            if last_page_number > max_page:
                max_page = int(last_page_number)
                art = Artist(name=artist.text, url=artist.a.attrs["href"])
        return art
