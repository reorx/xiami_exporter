import logging
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.easymp4 import EasyMP4
from mutagen.id3 import ID3, COMM
from mutagen.mp4 import MP4
from mutagen.id3._util import ID3NoHeaderError
from .models import Song


lg = logging.getLogger()

extra_id3_tags = [
    ('involvedpeople', 'TIPL'),
]


for k, v in extra_id3_tags:
    EasyID3.RegisterTextKey(k, v)


def comment_get(id3, key):
    return id3["COMM"]._pprint()


def comment_set(id3, key, value):
    # itunes can only identify:
    # COMM==eng=lorem ipsum
    try:
        frame = id3["COMM"]
    except KeyError:
        id3.add(COMM(
            encoding=3,
            lang='eng',
            text=value,
        ))
    else:
        frame.encoding = 3
        frame.lang = 'CHI'
        frame.text = value


def comment_delete(id3, key):
    del(id3["COMM"])


EasyID3.RegisterKey("comment", comment_get, comment_set, comment_delete)


def load_mp3(file_name, easy=True):
    try:
        if easy:
            return EasyID3(file_name)
        else:
            return ID3(file_name)
    except ID3NoHeaderError:
        # Fix mp3 file no tag loading error, m4a has no this problem
        id3 = ID3()
        id3.save(file_name)
        return EasyID3(file_name)


def load_m4a(file_name, easy=True):
    if easy:
        return EasyMP4(file_name)
    else:
        return MP4(file_name)


SUPPORT_EXTS = {
    '.mp3': load_mp3,
    '.m4a': load_m4a,
}

# database column name -> EasyID3 key
# https://id3.org/id3v2.3.0
# https://id3.org/id3v2.4.0-frames
DEFAULT_KEY_MAP = {
    'name': 'title',  # TIT2
    'sub_name': 'version',  # TIT3
    'album_name': 'album',  # TALB
    'album_lang': 'language',  # TLAN
    'track': 'tracknumber',  # TRCK
    # TPE2 by definition is "The 'Band/Orchestra/Accompaniment' frame, used for additional information about the performers in the recording"
    # but is repurposed for 'album artist' in various softwares https://stackoverflow.com/a/5958664/596206
    'artist_name': ['artist', 'albumartist'],  # TPE1, TPE2
    'songwriters': 'lyricist',  # TEXT
    'composer': 'composer',  # TCOM
    'arrangement': 'involvedpeople',  # TIPL
}


class Tagger:
    def __init__(self, file_name, file_path):
        self.file_name = Path(file_name)
        self.file_path = file_path
        self.mutagen_factory = SUPPORT_EXTS[self.file_name.suffix]
        self.mutagen_obj = self.mutagen_factory(file_path)
        # lg.debug('mutagen obj: %s', self.mutagen_obj)
        self.key_map = DEFAULT_KEY_MAP

    def get(self, key):
        mutagen_key = self.key_map[key]
        v = self.mutagen_obj.get(mutagen_key)
        if v:
            return v[0]
        return None

    def tag_by_model(self, song: Song, clear_old=False):
        lg.info(f'Tag song: {self.file_name}')

        if clear_old:
            # Delete old
            self.mutagen_obj.delete()
            # Create new
            self.mutagen_obj = self.mutagen_factory(self.file_path)

        # tags from key_map
        for song_key, _id3_key in self.key_map.items():
            v = getattr(song, song_key)
            # print('set', _id3_key, v)
            if isinstance(_id3_key, list):
                id3_keys = _id3_key
            else:
                id3_keys = [_id3_key]
            for id3_key in id3_keys:
                self.mutagen_obj[id3_key] = str(v)

        # other attrs: album_sub_name, artist_alias, singers

        # singers: performer -> TMCL
        singers = list(filter(None, (i.strip() for i in song.singers.split('/'))))
        if singers:
            self.mutagen_obj['performer'] = singers

        # album_sub_name, artist_alias: comments -> COMM
        comment_l = []
        for k in ['album_sub_name', 'artist_alias']:
            v = getattr(song, k, None)
            if v:
                comment_l.append(f'{k}: {v}')
        if comment_l:
            self.mutagen_obj['comment'] = '; '.join(comment_l)

        self.mutagen_obj.save()

    def show_tags(self):
        obj = self.mutagen_factory(self.file_path, easy=False)
        print(obj.pprint())
