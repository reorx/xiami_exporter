import logging
import hashlib
import json
import requests
from .http_util import get_cookie_from_cookiejar


class HTTPClient:
    def __init__(self, session, base_uri, headers=None):
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
        logging.debug(
            'HTTPClient request, %s, %s, %s, %s',
            method, url, args, kwargs)
        resp = getattr(self.session, method)(url, *args, **kwargs)
        logging.info('Response: %s, %s', resp.status_code, resp.content[:100])
        return resp

    def get(self, uri, *args, **kwargs):
        return self.request('get', uri, *args, **kwargs)

    def post(self, uri, *args, **kwargs):
        return self.request('post', uri, *args, **kwargs)

    def put(self, uri, *args, **kwargs):
        return self.request('put', uri, *args, **kwargs)

    def delete(self, uri, *args, **kwargs):
        return self.request('delete', uri, *args, **kwargs)

    # API methods

    def set_user_id(self, user_id):
        self.user_id  = user_id

    def make_q(self, page, page_size):
        q = {
            "userId": self.user_id,
            "type": 1,
            "pagingVO": {
                "page": page,
                "pageSize": page_size,
            },
        }
        return q

    def get_fav_songs(self, page, page_size=30):
        print(f'get_fav_songs: page={page}')
        uri = '/api/favorite/getFavorites'
        q = self.make_q(page, page_size)
        params = {
            '_q': param_json_dump(q),
            '_s': create_token(self.session, uri, q),
        }
        r = self.get(uri, params=params)
        # print(r.status_code, r.content.decode('utf-8'))
        data = r.json()

        # when out of max page, songs is "null"
        return data['result']['data']['songs']



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
