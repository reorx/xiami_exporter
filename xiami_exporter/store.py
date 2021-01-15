import os
import re
import json
import logging
from collections import OrderedDict
from .config import Config


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
        for root, dirs, files in os.walk(self.cfg.json_songs_dir):
            files.sort(key=lambda x: int(re.search(r'\d+', x).group()))
            lg.debug(f'sorted files: {files}')

            for file_name in files:
                file_path = os.path.join(self.cfg.json_songs_dir, file_name)
                self.load_song_json(file_path, songs_dict, str_id_dict)
        return songs_dict
