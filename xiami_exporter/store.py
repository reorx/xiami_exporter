from typing import Optional
from pathlib import Path
import os
import json
import logging
from collections import OrderedDict
from .config import Config
from .os_util import dir_files_sorted


lg = logging.getLogger('xiami.store')


class FileStore:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def load_song_json(self, file_path, songs_dict: OrderedDict, str_id_dict=None):
        with open(file_path, 'r') as f:
            data = json.loads(f.read())
        for song in data:
            songs_dict[song['songId']] = song
            if str_id_dict is not None:
                str_id_dict[song['songStringId']] = song

    def load_all_song_json(self, str_id_dict=None):
        songs_dict = OrderedDict()

        # read all song json files
        for file_name in dir_files_sorted(self.cfg.json_songs_dir):
            self.load_song_json(self.cfg.json_songs_dir.joinpath(file_name), songs_dict, str_id_dict)
        return songs_dict

    def find_cover_file(self, album_id) -> Optional[Path]:
        cover_files_dict = getattr(self, 'cover_files_dict', None)
        if not cover_files_dict:
            cover_files_dict = {}
            for _, _, files in os.walk(self.cfg.covers_dir):
                for file_name in files:
                    cover_files_dict[Path(file_name).stem] = file_name
            self.cover_files_dict = cover_files_dict

        file_name = cover_files_dict.get(str(album_id))
        if file_name:
            return self.cfg.covers_dir.joinpath(file_name)
