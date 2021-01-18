import time
import logging
import hashlib
import json
from contextlib import contextmanager
from enum import IntEnum
import requests
from .http_util import get_cookie_from_cookiejar


lg = logging.getLogger('xiami.client')


class FavType(IntEnum):
    SONGS = 1
    ALBUMS = 2
    ARTISTS = 3
    # MVS = 4
    PLAYLISTS = 5
    # not an actual fav type, put it here so that cli is easier to use
    MY_PLAYLISTS = 10


DEFAULT_PAGE_SIZE = 30


class HTTPClient:
    base_url = None

    def __init__(self, session: requests.Session, base_url=None, headers=None, wait_time=1):
        if base_url:
            self.base_url = base_url
        self.headers = headers or {}
        self.session = session
        self.wait_time = wait_time

    def request(self, method, uri, *args, **kwargs):
        if kwargs.pop('is_absolute_url', False):
            url = uri
        else:
            url = self.base_url + uri
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

        # wait for a little time, in case we are banned from the server
        time.sleep(self.wait_time)
        return resp

    def get(self, uri, *args, **kwargs):
        return self.request('get', uri, *args, **kwargs)

    def post(self, uri, *args, **kwargs):
        return self.request('post', uri, *args, **kwargs)


@contextmanager
def response_context(resp):
    try:
        yield None
    except KeyError:
        print(f'response: {resp.content.decode("utf8")}')
        raise


class XiamiClient(HTTPClient):
    base_url = 'https://www.xiami.com'
    fav_uri = '/api/favorite/getFavorites'

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
            '_s': create_token(self.session, self.fav_uri, q),
        }
        r = self.get(self.fav_uri, params=params)
        # print(r.status_code, r.content.decode('utf-8'))

        # when out of max page, songs is "null"
        with response_context(r):
            data = r.json()
            return data['result']['data']['songs']

    def get_fav_albums(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_fav_albums: page={page}')
        q = self.make_page_q(page, page_size, FavType.ALBUMS)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, self.fav_uri, q),
        }
        r = self.get(self.fav_uri, params=params)
        # print(r.status_code, r.content.decode('utf-8'))

        with response_context(r):
            data = r.json()
            return data['result']['data']['albums']

    def get_fav_artists(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_fav_albums: page={page}')
        q = self.make_page_q(page, page_size, FavType.ARTISTS)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, self.fav_uri, q),
        }
        r = self.get(self.fav_uri, params=params)
        # print(r.status_code, r.content.decode('utf-8'))

        with response_context(r):
            data = r.json()
            return data['result']['data']['artists']

    def get_fav_playlists(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_fav_playlists: page={page}')
        q = self.make_page_q(page, page_size, FavType.PLAYLISTS)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, self.fav_uri, q),
        }
        r = self.get(self.fav_uri, params=params)
        # print(r.status_code, r.content.decode('utf-8'))

        with response_context(r):
            data = r.json()
            return data['result']['data']['collects']

    def get_my_playlists(self, page, page_size=DEFAULT_PAGE_SIZE):
        lg.info(f'get_my_playlists: page={page}')
        uri = '/api/collect/getCollectByUser'
        q = {
            "userId": self.user_id,
            "type": 0,
            "pagingVO": {
                "page": page,
                "pageSize": page_size,
            },
            "includeSystemCreate": 1,
            "sort": 0,
        }
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, uri, q),
        }
        r = self.get(uri, params=params)
        # print(r.status_code, r.content.decode('utf-8'))

        with response_context(r):
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

        with response_context(r):
            data = r.json()
            return data['result']['data']['songPlayInfos']

    def get_playlist_detail(self, pl_id):
        lg.info(f'get_play_info: pl_id={pl_id}')

        uri_0 = '/api/collect/getCollectStaticUrl'
        q = {
            'listId': pl_id,
        }
        r_0 = self.get(uri_0, params={
            '_q': param_json_dump(q),
            '_s': create_token(self.session, uri_0, q),
        })
        data_0 = r_0.json()

        url = data_0['result']['data']['data']['data']['url']
        r = self.get(url, is_absolute_url=True)
        with response_context(r):
            data = r.json()
            return data['resultObj']

    def get_album_detail(self, album_id):
        lg.info(f'get_album_detail: album_id={album_id}')
        uri = '/api/album/getAlbumDetailNormal'
        q = {
            'albumId': album_id,
        }
        r = self.get(uri, params={
            '_q': param_json_dump(q),
            '_s': create_token(self.session, uri, q),
        })
        with response_context(r):
            data = r.json()
            return data['result']['data']['albumDetail']


def param_json_dump(o):
    return json.dumps(o, separators=(',', ':'))


def create_token(session, path, q=None):
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

    'listenFiles',  # only in get_playlist_detail
]


def trim_song(d):
    for k in song_useless_keys:
        if k in d:
            del d[k]


album_useless_keys = [
    'purviewRoleVOs',
    'purviewStatus',
    'userGrade',
    'userGradeComment',
]


def trim_album(d):
    for k in album_useless_keys:
        if k in d:
            del d[k]
