import os
import datetime
from typing import Optional
from requests.cookies import create_cookie
from http.cookiejar import Cookie
from mimetypes import guess_extension


def cookie_to_dict(c: Cookie):
    """
    Convert http.cookiejar.Cookie to a standarized dict.

    The schema of the dict is mostly the same with `result` in requests.cookies.create_cookie, which could be used to pass to that function after a little adjustments, see ``create_cookie_from_dict``.
    """
    assert isinstance(c, Cookie)
    result = {
        'name': '',
        'value': '',
        'port': None,
        'domain': '',
        'path': '/',
        'secure': False,
        'expires': None,
        'discard': True,
        'comment': None,
        'comment_url': None,
        # 'rest': {'HttpOnly': None},
        'version': 0,
        'rfc2109': False,
    }

    for k in result:
        result[k] = getattr(c, k)

    # handle Cookie._rest
    rest = dict(c._rest)
    if 'HttpOnly' in rest:
        del rest['HttpOnly']
        result['httponly'] = True
    else:
        result['httponly'] = False
    result['rest'] = rest
    return result


def create_cookie_from_dict(d: dict) -> Cookie:
    """
    Turn cookie dict into arguments for requests.cookies.create_cookie, and returns the calling.
    """

    kwargs = dict(d)
    args = [kwargs.pop('name'), kwargs.pop('value')]

    httponly = kwargs.pop('httponly')
    if httponly:
        kwargs['rest']['HttpOnly'] = None

    return create_cookie(*args, **kwargs)


def get_cookie_from_cookiejar(cj, name) -> Optional[Cookie]:
    for i in cj:
        if i.name == name:
            return i


def cookie_str_to_dict(s: str):
    d = {}
    for i in s.split(';'):
        line = i.strip()
        pos = line.find('=')
        d[line[:pos]] = line[pos + 1:]
    return d


def ensure_url_scheme(url):
    if not url.startswith('http://') and not url.startswith('https://'):
        return f'http://{url}'
    return url


def is_text_content(content_type):
    return content_type.startswith('text')


def content_type_to_ext(content_type):
    return guess_extension(content_type.partition(';')[0].strip())


def save_file(content: bytes, file_path, mode='wb'):
    with open(file_path, mode) as f:
        f.write(content)


def time_based_filename(ext):
    prefix = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return f'{prefix}{ext}'


def save_response_to_file(resp, file_path=None, dir_path=None, file_name=None, mode='wb', logger=None):
    if not file_path and not dir_path:
        raise ValueError('file_path and dir_path must have at least one')
    if not file_path:
        file_path = os.path.join(dir_path, file_name)
    if logger:
        logger.info(f'save response to {file_path}')
    save_file(resp.content, file_path)
