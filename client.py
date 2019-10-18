import argparse
import json
import random
import string
import sys
from pathlib import Path

import importer
import requests

# Page to tell users to visit to get a link code
LINK_CODE_HELP_URL = 'http://127.0.0.1:8000/link'


def random_client_id() -> str:
    """
    Return a random client id of 20 characters
    :return: random client id of 20 characters
    """
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(20))


def load_settings(settings_file: str) -> dict:
    """
    Returns dict containing settings in settings_file
    :raises json.JSONDecodeError if settings file is malformed
    :return: dict of settings in settings_file
    """
    if not Path(settings_file).is_file():
        open(settings_file, 'w').close()
    with open(settings_file, 'r+') as sfile:
        settings_str = sfile.read()
        if len(settings_str) > 0:
            settings = json.loads(sfile.read())
            # If id is missing then generate a random ID
            try:
                if settings.get('id'):
                    return settings
            except KeyError:
                pass
            settings['id'] = random_client_id()
            return settings
        else:
            return {'id': random_client_id()}


def save_settings(settings: dict, settings_file: str) -> None:
    """
    Save settings to settings_file overwriting its current contents
    :param settings: Settings dict to write to file
    :param settings_file: path to file to write to
    """
    with open(settings_file, 'w+') as sfile:
        sfile.write(json.dumps(settings))


def link_account(link_code: str, url: str, client_id: str) -> None:
    """
    Link to code link_code
    :param link_code: link code from website to link to
    :param url: base url to the website
    :param client_id: client id to link to
    :raises ConnectionError with server response body if response status code is not 200
    """
    response = requests.post(url + 'client-link/', data={'link': link_code, 'client': client_id})
    if response.status_code == 200:
        return
    raise ConnectionError(response.text)


def parse_args() -> dict:
    """
    Return parsed command line arguments
    :return: dict of parsed arguments
    """
    parser = argparse.ArgumentParser(description='Import playlist to playlstr')
    parser.add_argument('playlist', type=str, nargs='*', help='A playlist to import')
    parser.add_argument('-am', '--add-missing', action='store_true', help='Add tracks whose local file doesn\'t exist')
    parser.add_argument('-ha', '--hash', action='store_true', help='Use file hashes for track matching')
    parser.add_argument('--url', action='store', default='http://127.0.0.1:8000/', help='Website url')
    parser.add_argument('-l', '--link', type=str, action='store', default='',
                        help='Link with account. Go to {} to get a link code'.format(LINK_CODE_HELP_URL)),
    parser.add_argument('-xt', '--m3u-ext', action='store_true',
                        help='Use duration, artist, and track information from extended m3u instead of file metadata')
    parser.add_argument('-s', '--settings-file', default='./settings.txt', help='File to load settings from')
    return parser.parse_args().__dict__


def main() -> None:
    """
    Parse command line arguments and import specified playlists to the specified web server
    """
    args = parse_args()
    print(args)
    if len(args['playlist']) == 0:
        print('Specify at least one playlist for importing')
        sys.exit(0)
    # Load settings from file
    try:
        settings = load_settings(args['settings_file'])
    except json.JSONDecodeError:
        print('Error loading settings from {} (malformed file). Delete {} to fix this? (y/N)'.format(
            args['settings_file'], args['settings_file']))
        if input().lower() == 'y':
            open(args['settings'], 'w').close()
            settings = load_settings(args['settings_file'])
            save_settings(settings, args['settings_file'])
        else:
            sys.exit(0)
    # Link account if requested
    if args['link']:
        try:
            link_account(args['link'], args['url'], settings['id'])
        except ConnectionError as e:
            print('Error linking account ({}).'.format(e))
            sys.exit(1)
        print('Link successful')
        settings['link'] = args['link']
        save_settings(settings, args['settings_file'])
    if not settings.get('link'):
        print('No account linked. Get a link code from {} and run {} -l [code]'.format(LINK_CODE_HELP_URL, sys.argv[0]))
        sys.exit(0)
    # Ensure no trailing slash in server url
    args['url'] = args['url'].rstrip('/')
    # Parse playlists and upload them
    for playlist in args['playlist']:
        name, filetype = playlist.split('.')
        # Get the function for parsing the specified filetype
        try:
            parse_playlist = getattr(importer, 'import_{}'.format(filetype))
        except AttributeError:
            print('Invalid filetype ".{}"'.format(filetype))
            continue
        with open(playlist) as file:
            tracks = parse_playlist(file, args)
        response = requests.post('{}/client-import/'.format(args['url']),
                                 data={'playlist_name': name, 'tracks': json.dumps(tracks),
                                       'client_id': settings['id']})
        if response.status_code != 200:
            print('Error adding {}: {}'.format(playlist, response.reason))
        else:
            print('Imported {} to {}/list/{}/'.format(playlist, args['url'], response.text))


if __name__ == '__main__':
    main()
