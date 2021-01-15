import click
import json
import os
from pathlib import Path
from json import JSONEncoder
from .os_util import ensure_dir


class Config:
    dir_path = Path('XiamiExports')
    user_id = ''
    db_name = 'db.sqlite3'

    class Meta:
        file_path = 'config.json'
        keys = ['dir_path', 'user_id']

    # TODO use Path
    @property
    def json_songs_dir(self):
        return self.dir_path.joinpath('json', 'songs')

    @property
    def json_albums_dir(self):
        return self.dir_path.joinpath('json', 'albums')

    @property
    def json_playlists_dir(self):
        return self.dir_path.joinpath('json', 'playlists')

    @property
    def json_artists_dir(self):
        return self.dir_path.joinpath('json', 'artists')

    @property
    def music_dir(self):
        return self.dir_path.joinpath('music')

    @property
    def covers_dir(self):
        return self.dir_path.joinpath('covers')

    @property
    def artist_logos_dir(self):
        return self.dir_path.joinpath('artist_logos')

    @property
    def db_path(self):
        return self.dir_path.joinpath(self.db_name)

    def load(self):
        with open(self.Meta.file_path, 'r') as f:
            d = json.loads(f.read())
        for k, v in d.items():
            setattr(self, k, v)

        # load from env
        _dir_path = os.environ.get('XME_DIR_PATH')
        if _dir_path:
            self.dir_path = _dir_path

        if isinstance(self.dir_path, str):
            self.dir_path = Path(self.dir_path)

        ensure_dir(self.dir_path)

    def save(self):
        d = {}
        for k in self.Meta.keys:
            d[k] = getattr(self, k)
        with open(self.Meta.file_path, 'w') as f:
            content = json.dumps(d, indent=2, cls=CustomJSONEncoder)
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


class CustomJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, Path):
            return str(o)
        else:
            return super().default(o)
