import json
import os
import time
import logging
from xiami_exporter.client import HTTPClient


dir_path = 'exports'

logging.basicConfig(level=logging.INFO)


def main():
    import fetch
    from xiami_exporter.fetch_importer import session

    client = HTTPClient(
        session,
        'https://www.xiami.com',
    )

    client.set_user_id("932367")

    page = 1
    while True:
        songs = client.get_fav_songs(page)
        if not songs:
            break
        file_path = os.path.join(dir_path, f'songs-{page}.json')
        with open(file_path, 'w') as f:
            json.dump(songs, f)
        page += 1
        time.sleep(1)


if __name__ == '__main__':
    main()
