import argparse
import json
import random
import string
import sys
from pathlib import Path
from typing import Optional

import importer
import requests

LINK_HELP_URL = 'http://127.0.0.1:8000/link'
SETTINGS_FILE = './settings.txt'


def random_client_id():
    """
    Return a random client id of 20 characters
    :return: random client id of 20 characters
    """
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for i in range(20))


def load_settings():
    """
    Load settings in SETTINGS_FILE into the settings
    :raises json.JSONDecodeError if settings file is malformed
    """
    global settings
    if not Path(SETTINGS_FILE).is_file():
        open(SETTINGS_FILE, 'w').close()
    with open(SETTINGS_FILE, 'r+') as sfile:
        settings_str = sfile.read()
        if len(settings_str) > 0:
            settings = json.loads(sfile.read())
            if settings.get('id'):
                return
            settings['id'] = random_client_id()
        else:
            settings = {'id': random_client_id()}


def save_settings():
    """
    Save settings to SETTINGS_FILE
    """
    global settings
    with open(SETTINGS_FILE, 'w+') as sfile:
        sfile.write(json.dumps(settings))


def link_account(link_code: str, url: str, client_id: str) -> Optional[str]:
    """
    Link to code link_code
    :return: Error message on error or None on success
    """
    response = requests.post(url + 'client-link/', data={'link': link_code, 'client': client_id})
    if response.status_code == 200:
        return None
    return response.text


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Import playlist to playlstr')
    parser.add_argument('playlist', type=str, nargs='*', help='A playlist to import')
    parser.add_argument('-am', '--add-missing', action='store_true', help='Add tracks whose local file doesn\'t exist')
    parser.add_argument('-ha', '--hash', action='store_true', help='Use file hashes for track matching')
    parser.add_argument('-l', '--link', type=str, action='store', default=-1,
                        help='Link with account. Go to {} to get a link code'.format(LINK_HELP_URL)),
    parser.add_argument('-xt', '--m3u-ext', action='store_true',
                        help='Use duration, artist, and track information from extended m3u instead of file metadata')
    parser.add_argument('--url', action='store', default='http://127.0.0.1:8000/', help='Website url')
    args = parser.parse_args().__dict__
    global settings
    try:
        load_settings()
    except json.JSONDecodeError:
        print('Error loading settings from {} (malformed file). Delete {} to fix this? (y/N)')
        if input().lower() == 'y':
            open(SETTINGS_FILE, 'w').close()
            load_settings()
            save_settings()
        else:
            sys.exit(0)
    if args['link'] != -1:
        link_result = link_account(args['link'], args['url'], settings['id'])
        if link_result:
            print('Error linking account ({}).'.format(link_result))
            sys.exit(0)
        else:
            print('Link successful')
            settings['link'] = args['link']
            save_settings()
    if not settings.get('link'):
        print('No account linked. Get a link code from {} and run {} -l [code]'.format(LINK_HELP_URL, sys.argv[0]))
        sys.exit(0)
    # Ensure trailing slash
    if args['url'][-1] == '/':
        args['url'] = args['url'][:-1]
    if len(args['playlist']) == 0:
        print('No playlist selected for exporting')
        sys.exit(0)
    for playlist in args['playlist']:
        split_dot = playlist.split('.')
        filetype = split_dot[-1]
        name = split_dot[0]
        try:
            parse_method = getattr(importer, 'import_{}'.format(filetype))
        except AttributeError:
            print('Invalid filetype {}'.format(filetype))
            continue
        with open(playlist) as file:
            tracks = parse_method(file, args)
        response = requests.post('{}/client-import/'.format(args['url']),
                                 data={'playlist_name': name, 'tracks': json.dumps(tracks),
                                       'client_id': settings['id']})
        if response.status_code != 200:
            print('Error adding {}: {}'.format(playlist, response.reason))
        else:
            print('Imported {}: {}/list/{}/'.format(playlist, args['url'], response.text))
