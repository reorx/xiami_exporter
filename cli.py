import json
import os
import sys
import time
import logging
import click
from xiami_exporter.client import XiamiClient
from xiami_exporter.fetch_importer import load_fetch_module


lg = logging.getLogger('cli')

logging.basicConfig(level=logging.INFO)
# logging.basicConfig(level=logging.DEBUG)


class Config:
    dir_path = 'XiamiExports'
    user_id = ''

    class Meta:
        file_path = 'config.json'
        keys = ['dir_path', 'user_id']

    @classmethod
    def load(cls):
        with open(cls.Meta.file_path, 'r') as f:
            d = json.loads(f.read())
        for k, v in d.items():
            setattr(cls, k, v)

    @classmethod
    def save(cls):
        d = {}
        for k in cls.Meta.keys:
            d[k] = getattr(cls, k)
        with open(cls.Meta.file_path, 'w') as f:
            content = json.dumps(d, indent=2)
            click.echo(f'\nWrite config to {cls.Meta.file_path}\n{content}')
            f.write(content)

    @classmethod
    def update_from_input(cls):
        click.echo('\nInput config')
        for k in cls.Meta.keys:
            hint = ''
            _v = getattr(cls, k)
            if _v:
                hint = f' (default "{_v}")'
            v = input(f'  {k}{hint}: ')
            if not v:
                v = _v
            setattr(cls, k, v)


@click.group()
def cli():
    pass


def check_fetch():
    file_path = 'fetch.py'
    if not os.path.exists(file_path):
        click.echo('fetch.py not found, please create the file by pasting "Copy as Node.js fetch" from Chrome.')
        click.echo('For more detailed instructions, please read https://github.com/reorx/xiami_exporter')
        sys.exit(1)

    load_fetch_module(file_path)


@cli.command()
def init():
    if os.path.exists(Config.Meta.file_path):
        if click.confirm('config file exists, continue to rewrite it'):
            Config.update_from_input()
            Config.save()
    else:
        Config.update_from_input()
        Config.save()


def get_client():
    check_fetch()

    from xiami_exporter.fetch_importer import session

    client = XiamiClient(session)
    return client


@cli.command(help='export fav songs as json files')
@click.option('--page', '-p', default='', help='page number, if omitted, all pages will be exported')
def export_fav_songs(page):
    pass


def main():
    import fetch  # noqa
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
        file_path = os.path.join(Config.dir_path, f'songs-{page}.json')
        with open(file_path, 'w') as f:
            json.dump(songs, f)
        page += 1
        time.sleep(1)


if __name__ == '__main__':
    cli()
