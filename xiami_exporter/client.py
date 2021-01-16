import logging
import hashlib
import json
import requests
from .http_util import get_cookie_from_cookiejar
from enum import IntEnum


lg = logging.getLogger('xiami.client')


class FavType(IntEnum):
    SONGS = 1
    ALBUMS = 2
    ARTISTS = 3
    # MVS = 4
    PLAYLISTS = 5


DEFAULT_PAGE_SIZE = 30


class HTTPClient:
    base_uri = None

    def __init__(self, session: requests.Session, base_uri=None, headers=None):
        if base_uri:
            self.base_uri = base_uri
        self.headers = headers or {}
        self.session = session

    def request(self, method, uri, *args, **kwargs):
        url = self.base_uri + uri
        if 'headers' in kwargs:
            headers = dict(self.headers)
            headers.update(kwargs['headers'])
            kwargs['headers'] = headers
        else:
            if self.headers:
                kwargs['headers'] = self.headers

        if 'json_data' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('json_data'))
            if 'headers' in kwargs:
                kwargs['headers'].update({
                    'Content-Type': 'application/json',
                })
        lg.debug(
            'HTTPClient request, %s, %s, %s, %s',
            method, url, args, kwargs)
        resp = getattr(self.session, method)(url, *args, **kwargs)
        lg.debug('Response: %s, %s', resp.status_code, resp.content[:100])
        return resp

    def get(self, uri, *args, **kwargs):
        return self.request('get', uri, *args, **kwargs)

    def post(self, uri, *args, **kwargs):
        return self.request('post', uri, *args, **kwargs)


class XiamiClient(HTTPClient):
    base_uri = 'https://www.xiami.com'
    fav_path = '/api/favorite/getFavorites'

    def __init__(self, session, headers=None):
        super().__init__(session, headers=headers)

    # API methods

    def set_user_id(self, user_id):
        self.user_id = user_id

    def make_page_q(self, page, page_size, fav_type=FavType.SONGS):
        q = {
            "userId": self.user_id,
            "type": fav_type,
            "pagingVO": {
                "page": page,
                "pageSize": page_size,
            },
        }
        return q

    def get_fav_songs(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_fav_songs: page={page}')
        q = self.make_page_q(page, page_size, FavType.SONGS)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, self.fav_path, q),
        }
        r = self.get(self.fav_path, params=params)
        # print(r.status_code, r.content.decode('utf-8'))
        data = r.json()

        # when out of max page, songs is "null"
        return data['result']['data']['songs']

    def get_fav_albums(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_fav_albums: page={page}')
        q = self.make_page_q(page, page_size, FavType.ALBUMS)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, self.fav_path, q),
        }
        r = self.get(self.fav_path, params=params)
        # print(r.status_code, r.content.decode('utf-8'))
        data = r.json()

        return data['result']['data']['albums']

    def get_fav_artists(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_fav_albums: page={page}')
        q = self.make_page_q(page, page_size, FavType.ARTISTS)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, self.fav_path, q),
        }
        r = self.get(self.fav_path, params=params)
        # print(r.status_code, r.content.decode('utf-8'))
        data = r.json()

        return data['result']['data']['artists']

    def get_fav_playlists(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_fav_playlists: page={page}')
        q = self.make_page_q(page, page_size, FavType.PLAYLISTS)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, self.fav_path, q),
        }
        r = self.get(self.fav_path, params=params)
        # print(r.status_code, r.content.decode('utf-8'))
        data = r.json()

        return data['result']['data']['collects']

    def get_play_info(self, song_ids):
        lg.info(f'get_play_info: song_ids={song_ids}')
        uri = '/api/song/getPlayInfo'
        q = {
            'songIds': song_ids,
        }
        r = self.get(uri, params={
            '_q': param_json_dump(q),
            '_s': create_token(self.session, uri, q),
        })
        data = r.json()

        return data['result']['data']['songPlayInfos']


def param_json_dump(o):
    return json.dumps(o, separators=(',', ':'))


def create_token(session, path, q):
    tk = get_cookie_from_cookiejar(session.cookies, 'xm_sg_tk')
    if not tk:
        raise ValueError('could not get xm_sg_tk from cookie')
    if q:
        q_json = param_json_dump(q)
    else:
        q_json = ''
    token_value = tk.value.split('_')[0] + '_xmMain_' + path + '_' + q_json
    token = get_md5_hex(token_value.encode())
    return token


def get_md5_hex(b: bytes):
    return hashlib.md5(b).hexdigest()


song_useless_keys = [
    'favFlag',
    'thirdpartyUrl',
    'boughtCount',
    'gmtCreate',
    'playCount',
    'shareCount',
    'favCount',
    'offline',
    'offlineType',
    'downloadCount',
    'originOffline',
    'canReward',
    'isFavor',
    'purviewRoleVOs',
    'artistVOs',  # duplicated with 'singerVOs'
    'tags',
    'thirdSongs',
    'freeAudioInfo',
    'whaleSongVO',
]


def trim_song(d):
    for k in song_useless_keys:
        if k in d:
            del d[k]
