import json
import os
import sys
import time
import logging
import click
from xiami_exporter.client import XiamiClient
from xiami_exporter.fetch_loader import load_fetch_module
from xiami_exporter.io import ensure_dir


lg = logging.getLogger('cli')

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)


class Config:
    dir_path = 'XiamiExports'
    user_id = ''

    class Meta:
        file_path = 'config.json'
        keys = ['dir_path', 'user_id']

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


if __name__ == '__main__':
    cli()
