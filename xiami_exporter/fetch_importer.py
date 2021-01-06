import json
import requests
from requests.cookies import cookiejar_from_dict
from requests.utils import dict_from_cookiejar
from urllib.parse import urlparse, parse_qs
from .http_util import cookie_str_to_dict
from .client import create_token

__all__ = ['null', 'fetch']


# nodejs global
null = None

session = None


def fetch(url, args):
    global session

    url_parsed = urlparse(url)
    params = parse_qs(url_parsed.query)
    param_q = None
    if '_q' in params:
        param_q = params['_q'][0]
    param_s = None
    if '_s' in params:
        param_s = params['_s'][0]

    # # recalculate param_s
    # tk = '32056b7abf66fd42bddfc24e575c6107_1609856909772'
    # v = tk.split('_')[0] + '_xmMain_' + url_parsed.path + '_' + json.dumps(json.loads(param_q), separators=(',', ':'))
    # print(f'recal token value: {v}')
    # print(f'recal  token: {get_md5_hex(v.encode())}')
    # print(f'actual token: {param_s}')


    headers = args['headers']
    cookies = cookie_str_to_dict(headers['cookie'])
    # print(cookies)

    s = requests.Session()
    cookiejar = cookiejar_from_dict(cookies)
    # print(cookiejar)
    # print(s.cookies)
    s.cookies = cookiejar

    # r = s.get('http://httpbin.org/cookies')
    # print(r.json())
    r = s.get(url)
    """
    Possible responses:
    - {'code': 'SG_TOKEN_EXPIRED', 'msg': '令牌过期'}
    - {"code":"SG_INVALID","msg":"请求无效"}
    """
    data = r.json()
    if data['code'] == 'SUCCESS':
        session = s
        print(f'test fetch() ok')
        if param_s:
            q_dict = None
            if param_q:
                q_dict = json.loads(param_q)
            token = create_token(s, url_parsed.path, q_dict)
            if token == param_s:
                print(f'recal token correct: {token}')
            else:
                print(f'recal token unequal:\n- recal : {token}\n- actual: {param_s}')
                raise Exception('stop proceessing due to token recal failure')
    # print(data, r.headers)
    # print(dict_from_cookiejar(s.cookies))


def load_fetch_module(file_path):
    with open(file_path, 'r') as f:
        exec(f.read())
