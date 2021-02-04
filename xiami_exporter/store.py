from typing import Optional
from pathlib import Path
import re
import os
import json
import logging
from collections import OrderedDict
from .config import Config
from .os_util import dir_files_sorted, dir_files


lg = logging.getLogger('xiami.store')


REGEX_MUSIC_FILE = re.compile(r'^\d+-(\d+)\.')


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
        cfg = self.cfg
        songs_dict = OrderedDict()

        # read all song json files
        for file_name in dir_files_sorted(cfg.json_songs_dir):
            self.load_song_json(cfg.json_songs_dir.joinpath(file_name), songs_dict, str_id_dict)

        # read from details dir
        for details_dir in [cfg.json_albums_details_dir, cfg.json_playlists_details_dir, cfg.json_my_playlists_details_dir]:
            for file_name in dir_files_sorted(details_dir):
                with open(details_dir.joinpath(file_name), 'r') as f:
                    detail = json.loads(f.read())
                for song_data in detail['songs']:
                    songs_dict[song_data['songId']] = song_data
                    if str_id_dict is not None:
                        str_id_dict[song_data['songStringId']] = song_data
        return songs_dict

    def load_music_files(self, dir_path=None):
        files_dict = {}
        for file_name, file_path, song_id in self.yield_music_files(dir_path=dir_path):
            files_dict[song_id] = (file_name, file_path)
        return files_dict

    def yield_music_files(self, dir_path=None):
        if not dir_path:
            dir_path = self.cfg.music_dir
        for file_name in dir_files(dir_path):
            rv = REGEX_MUSIC_FILE.search(file_name)
            if not rv:
                lg.info(f'file {file_name}: skip for name not match ROW_NUMBER-SONG_ID.mp3 file pattern')
                continue
            song_id = int(rv.groups()[0])
            yield file_name, dir_path.joinpath(file_name), song_id

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
