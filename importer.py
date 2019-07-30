from hashlib import md5
from io import TextIOWrapper

import mutagen as mu


def import_m3u(file: TextIOWrapper, args: dict) -> list:
    """
    Return a list of files in the playlist and their information
    :param file: the m3u file
    :param args: additional options
    :return:
    """
    first = file.readline().rstrip()
    if first == '#EXTM3U':
        ext = True
        on_inf = True  # Whether we are on a #EXTINF line
    else:
        file.seek(0)
        on_inf = False  # Whether we are on a #EXTINF line
        ext = False
    inf_duration = None
    inf_artist = None
    inf_track = None
    tracks = []
    for line in file:
        line = line.rstrip()
        if on_inf:
            line = line[7:]
            split_colon = line.split(':')
            inf_duration = split_colon[0] if len(split_colon) > 0 else None
            split_dash = line.split('-')
            inf_artist = split_dash[0].strip().split(',', 1)[1] if len(split_dash) > 0 else None
            inf_track = split_dash[1] if len(split_dash) > 1 else None
            on_inf = False
            continue
        else:
            # Get file tags
            try:
                f = mu.File(line)
                info = {k.lower(): v for k, v in f.tags}
                info['duration'] = f.info.length
            except mu.MutagenError:
                info = {'filename': line}
            except KeyError:
                pass
            # Added info from m3u extended
            if ext:
                on_inf = True
                if args['m3u_ext']:
                    info['title'] = inf_track
                    info['artist'] = inf_artist
                    info['duration'] = inf_duration
                else:
                    if 'title' not in info or len(info['title']) == 0:
                        info['title'] = inf_track
                    if 'artist' not in info or len(info['artist']) == 0:
                        info['arist'] = inf_artist
                    if 'duration' not in info or info['duration'] == 0:
                        info['duration'] = inf_duration
            if args['hash']:
                try:
                    with open(line, 'rb') as hash_file:
                        hasher = md5()
                        buffer = hash_file.read()
                        hasher.update(buffer)
                        info['hash'] = hasher.hexdigest()
                except FileNotFoundError:
                    pass
            info['duration'] = round(info['duration'])
            tracks.append(info)
    return tracks
