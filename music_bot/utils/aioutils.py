from aiohttp import ClientSession

from bs4 import BeautifulSoup

from music_bot.scrap.models import Artist
from music_bot.settings import BASE_URL


async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

# This function is not used in program, but rather in debugging and testing.
async def artist_with_most_pages() -> Artist:
    async with ClientSession() as session:
        response = await fetch(session, BASE_URL)
        bs = BeautifulSoup(response, "html.parser")
        artists = bs.find("aside", class_="rwr").find_all("li")
        max_page = 0
        for artist in artists:
            response = await fetch(session, artist.a.attrs["href"])
            art_bs = BeautifulSoup(response, "html.parser")
            try:
                last_page_url = (
                    art_bs.find("div", class_="pnavifa fxmf")
                    .find_all("a")[-1]
                    .attrs["href"]
                )
            except AttributeError:
                continue
            last_page_index = last_page_url.split("/")[-2]
            if int(last_page_index) > max_page:
                max_page = int(last_page_index)
                art = Artist(name=artist.text, url=artist.a.attrs["href"])
        return art
