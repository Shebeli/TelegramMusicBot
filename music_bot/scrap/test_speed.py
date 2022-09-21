import cProfile
import pstats
import time
import asyncio

from music_bot.scrap.scrap import get_artist, all_artist_songs_paginated


async def main():

    with cProfile.Profile() as pr:
        artist = await get_artist("محمود کریمی")
        songs = await all_artist_songs_paginated(artist)
        stats = pstats.Stats(pr)
        stats.sort_stats(pstats.SortKey.TIME)
        stats.print_stats()
        stats.dump_stats("profile.prof")
    return songs


if __name__ == "__main__":
    start = time.perf_counter()
    songs = asyncio.run(main())
    print(f"Downloade {len(songs)} pages in {time.perf_counter() - start} seconds.")
