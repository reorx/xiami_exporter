import os
import re
import logging


lg = logging.getLogger('xiami.os_util')


def ensure_dir(path):
    # lg.debug('ensure dir: {}'.format(path))
    if os.path.exists(path):
        if not os.path.isdir(path):
            raise IOError('ensure_dir: {} must be a directory'.format(path))
    else:
        lg.debug('mkdir %s', path)
        try:
            os.makedirs(path)
        except OSError as e:
            lg.info('ignore os.makedirs OSError: %s', e)


REGEX_FILE_NUMBER = re.compile(r'\d+')


def dir_files_sorted(dir_path):
    _, _, files = next(os.walk(dir_path))
    files.sort(key=lambda x: int(re.search(REGEX_FILE_NUMBER, x).group()))
    for i in files:
        yield i
