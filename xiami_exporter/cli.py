import json
import re
import os
import sys
import time
import logging
import click
from urllib.parse import urlparse
from .client import XiamiClient
from .fetch_loader import load_fetch_module
from .io import ensure_dir
from .litekv import LiteKV
from .http_util import save_response_to_file


lg = logging.getLogger('cli')

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)


class Config:
    dir_path = 'XiamiExports'
    user_id = ''
    db_name = 'db.sqlite3'

    class Meta:
        file_path = 'config.json'
        keys = ['dir_path', 'user_id']

    # TODO use Path
    @property
    def json_songs_dir(self):
        return os.path.join(self.dir_path, 'json', 'songs')

    @property
    def json_albums_dir(self):
        return os.path.join(self.dir_path, 'json', 'albums')

    @property
    def json_playlists_dir(self):
        return os.path.join(self.dir_path, 'json', 'playlists')

    @property
    def json_artists_dir(self):
        return os.path.join(self.dir_path, 'json', 'artists')

    @property
    def music_dir(self):
        return os.path.join(self.dir_path, 'music')

    @property
    def covers_dir(self):
        return os.path.join(self.dir_path, 'covers')

    @property
    def db_path(self):
        return os.path.join(self.dir_path, self.db_name)

    def load(self):
        with open(self.Meta.file_path, 'r') as f:
            d = json.loads(f.read())
        for k, v in d.items():
            setattr(self, k, v)

        # load from env
        _dir_path = os.environ.get('XME_DIR_PATH')
        if _dir_path:
            self.dir_path = _dir_path

        ensure_dir(self.dir_path)

    def save(self):
        d = {}
        for k in self.Meta.keys:
            d[k] = getattr(self, k)
        with open(self.Meta.file_path, 'w') as f:
            content = json.dumps(d, indent=2)
            click.echo(f'\nWrite config to {self.Meta.file_path}\n{content}')
            f.write(content)

    def update_from_input(self):
        click.echo('\nInput config')
        for k in self.Meta.keys:
            hint = ''
            _v = getattr(self, k)
            if _v:
                hint = f' (default "{_v}")'
            v = input(f'  {k}{hint}: ')
            if not v:
                v = _v
            setattr(self, k, v)


cfg = Config()


def check_fetch():
    file_path = 'fetch.py'
    if not os.path.exists(file_path):
        click.echo('fetch.py not found, please create the file by pasting "Copy as Node.js fetch" from Chrome.')
        click.echo('For more detailed instructions, please read https://github.com/reorx/xiami_exporter')
        sys.exit(1)

    return load_fetch_module(file_path)


def get_client():
    session = check_fetch()
    client = XiamiClient(session)
    client.set_user_id(cfg.user_id)
    return client


def get_db():
    return LiteKV(cfg.db_path)


@click.group()
def cli():
    pass


@cli.command()
def init():
    if os.path.exists(cfg.Meta.file_path):
        if click.confirm('config file exists, continue to rewrite it'):
            cfg.update_from_input()
            cfg.save()
    else:
        cfg.update_from_input()
        cfg.save()


@cli.command()
def check():
    check_fetch()
    click.echo('Success, you can now use the export commands')


@cli.command(help='export fav songs as json files')
@click.option('--page', '-p', default='', help='page number, if omitted, all pages will be exported')
def export_fav_songs(page):
    cfg.load()
    client = get_client()

    if page:
        get_once = True
    else:
        get_once = False
        page = 1

    ensure_dir(cfg.json_songs_dir)
    while True:
        songs = client.get_fav_songs(page)
        if not songs:
            break
        file_path = os.path.join(cfg.json_songs_dir, f'songs-{page}.json')
        with open(file_path, 'w') as f:
            json.dump(songs, f)

        if get_once:
            break
        page += 1
        time.sleep(1)


def download_songs(songs, client, db):
    """
    songs:
    {
        id:
        name:
        album:
    }
    """
    ensure_dir(cfg.music_dir)
    song_ids = []
    for i in songs:
        song_id = i['id']
        song_ids.append(song_id)
        song_store = db.get(song_id)
        if not song_store:
            song_store = dict(i)
            song_store.update({
                'download_status': 0,
            })
            db.set(song_id, json.dumps(song_store))

    items = client.get_play_info(song_ids)
    for item in items:
        song_store = json.loads(db.get(item['songId']))
        playinfo = sorted(item['playInfos'], key=lambda x: x['fileSize'], reverse=True)[0]
        if playinfo['fileSize'] == 0:
            print(f'no valid file in playinfo: id={song_store["id"]}  name={song_store["name"]} album={song_store["album"]}')
            song_store['download_status'] = -1
            db.set(song_store['id'], json.dumps(song_store))
            continue

        # print(playinfo)
        url = playinfo['listenFile']
        resp = client.session.get(url)
        url_parsed = urlparse(url)
        file_name = os.path.basename(url_parsed.path)
        if song_store['name']:
            _, ext = os.path.splitext(file_name)
            file_name = song_store['name'] + ext

        file_path = os.path.join(cfg.music_dir, file_name)
        save_response_to_file(resp, file_path=file_path, logger=lg)


def load_song_json(file_path, songs_dict, songs_list):
    with open(file_path, 'r') as f:
        data = json.loads(f.read())
    for song in data:
        songs_dict[song['songId']] = song
        songs_list.append(song)


@cli.command(help='export fav songs as json files')
@click.argument('file', default='')
@click.option('--song-id', '-i', default='', help='song id, in all number format (e.g. 1769839259)')
@click.option('--force', '-f', default='', help='force re-download even if song was downloaded (according to db)')
def download_music(file, song_id, force):
    cfg.load()
    db = get_db()

    if song_id:
        song_ids = song_id.split(',')
        songs = []
        for i in song_ids:
            songs.append({
                'id': i,
                'name': '',
                'album': '',
                'bak_id': '',
            })
        download_songs(songs, get_client(), db)
    else:
        if not file:
            click.echo('file is required if no song ids are provided')
            sys.exit(1)

        songs_dict = {}
        songs_list = []
        if file == 'all':
            # read all song json files
            for root, dirs, files in os.walk(cfg.json_songs_dir):
                files.sort(key=lambda x: int(re.search('\d+', x).group()))
                print(files)
                for file_name in files:
                    file_path = os.path.join(cfg.json_songs_dir, file_name)
                    load_song_json(file_path, songs_dict, songs_list)

        for song in songs_list:
            # if song['musicType'] == 0:
            if song['bakSongId'] != 0:
                print(f'{song["songId"]}: {song["songName"]} - {song["albumName"]} - {song["artistName"]}')


if __name__ == '__main__':
    cli()
