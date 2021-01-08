from pathlib import Path
import json
import re
import os
import sys
import time
import logging
import click
from collections import OrderedDict
from urllib.parse import urlparse
from .client import XiamiClient
from .fetch_loader import load_fetch_module
from .io import ensure_dir
from .http_util import save_response_to_file
from .config import cfg
from .models import db, create_song, all_models, Song, DownloadStatus


lg = logging.getLogger('cli')

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)


DEFAULT_UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36'


def check_fetch():
    file_path = 'fetch.py'
    if not os.path.exists(file_path):
        click.echo('fetch.py not found, please create the file by pasting "Copy as Node.js fetch" from Chrome.')
        click.echo('For more detailed instructions, please read https://github.com/reorx/xiami_exporter')
        sys.exit(1)

    return load_fetch_module(file_path)


def get_client():
    session, headers = check_fetch()
    # change headers
    headers['User-Agent'] = DEFAULT_UA
    client = XiamiClient(session, headers=headers)
    client.set_user_id(cfg.user_id)
    return client


def prepare_db():
    db.init(cfg.db_path)

    db.create_tables(all_models)


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
def export_songs(page):
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


def load_song_json(file_path, songs_dict: OrderedDict):
    with open(file_path, 'r') as f:
        data = json.loads(f.read())
    for song in data:
        songs_dict[song['songId']] = song


def load_all_song_json():
    songs_dict = OrderedDict()

    # read all song json files
    for root, dirs, files in os.walk(cfg.json_songs_dir):
        files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
        lg.debug(f'sorted files: {files}')

        for file_name in files:
            file_path = os.path.join(cfg.json_songs_dir, file_name)
            load_song_json(file_path, songs_dict)
    return songs_dict


@cli.command(help='create songs in database')
@click.option('--clear', '-c', is_flag=True, help='clear db before inserting')
def create_songs_db(clear):
    cfg.load()
    prepare_db()
    if clear:
        for model in all_models:
            model.delete().execute()

    songs_dict = load_all_song_json()
    row_number = 0
    for data in songs_dict.values():
        row_number += 1
        try:
            create_song(data, row_number)
        except Exception:
            print(f'created songs: {row_number}')
            raise
    print(f'create songs done, total: {row_number}')


def get_effective_playinfo(song_id, playinfos):
    playinfo = sorted(playinfos, key=lambda x: x['fileSize'], reverse=True)[0]
    if playinfo['fileSize'] == 0:
        lg.debug(f'no valid file in playinfo: id={song_id}')
        return
    return playinfo


def get_audioinfos(client, song_ids, try_bak_id=True):
    urls_dict = {}
    for item in client.get_play_info(song_ids):
        # get effective playinfo
        song_id = item["songId"]
        playinfo = get_effective_playinfo(song_id, item['playInfos'])
        if playinfo:
            urls_dict[song_id] = playinfo['listenFile']

    audioinfos = []
    for song_id in song_ids:
        url = urls_dict.get(song_id)
        info = {
            'song_id': song_id,
            'url': url,
        }
        audioinfos.append(info)
        if not url:
            if not try_bak_id:
                continue
            song = Song.get(Song.id == song_id)
            if not song.bak_song_id:
                continue
            lg.info(f'try bak_song_id {song.bak_song_id} for {song.id}')
            for item in client.get_play_info([song.bak_song_id]):
                playinfo = get_effective_playinfo(item['songId'], item['playInfos'])
                if playinfo:
                    info['url'] = playinfo['listenFile']

    return audioinfos


def download_songs(client, audioinfos, update_db=True):
    ensure_dir(cfg.music_dir)

    for info in audioinfos:
        song_id = info['song_id']
        if update_db:
            song = Song.get(Song.id == song_id)
            prefix = f'{song.row_number}-'
        else:
            song = None
            prefix = ''

        url = info['url']
        if url:
            url_parsed = urlparse(url)
            _file_name = os.path.basename(url_parsed.path)
            ext = Path(_file_name).suffix
            file_name = f'{prefix}{song.id}{ext}'

            resp = client.session.get(url)

            file_path = cfg.music_dir.joinpath(file_name)
            try:
                save_response_to_file(resp, file_path=file_path, logger=lg)
            except Exception as e:
                download_status = DownloadStatus.FAILED
                lg.error(f'failed to download {file_name}: {e}')
            else:
                download_status = DownloadStatus.SUCCESS
        else:
            download_status = DownloadStatus.UNAVAILABLE

        lg.info(f'download status of {song_id}: {DownloadStatus.to_str(download_status)}')
        if song:
            song.download_status = download_status
            song.save()


@cli.command(help='download songs mp3')
@click.option('--song-id', '-i', default='', help='only download song(s) by id, comma separated')
@click.option('--filter-status', default=DownloadStatus.NOT_SET, help='filter Song.download_status')
@click.option('--batch-size', default=10, help='number of songs in a batch download task')
@click.option('--batch-count', default=0, help='number of batch download tasks')
def download_music(song_id, filter_status, batch_size, batch_count):
    cfg.load()
    prepare_db()
    client = get_client()

    if song_id:
        song_ids = song_id.split(',')
        audioinfos = get_audioinfos(client, song_ids, try_bak_id=False)
        download_songs(client, audioinfos)
    else:
        def yield_songs(size):
            songs = []
            for song in Song.select().where(Song.download_status == filter_status).order_by(Song.row_number):
                songs.append(song)
                if len(songs) == size:
                    yield songs
                    songs = []
            if songs:
                yield songs

        _batch_count = 0
        for songs in yield_songs(batch_size):
            _batch_count += 1
            if _batch_count > batch_count:
                break
            audioinfos = get_audioinfos(client, [i.id for i in songs])
            download_songs(client, audioinfos)


if __name__ == '__main__':
    cli()
