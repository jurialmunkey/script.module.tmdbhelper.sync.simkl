from re import fullmatch
from datetime import datetime, timezone
from jurialmunkey.parser import try_int
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper_sync_simkl.identifiers import SimklIdentifiers


def latest(values):
    return max(
        (value for value in values if value), default=None,
        key=lambda value: datetime.fromisoformat(value.replace('Z', '+00:00')))


def utc_timestamp(value):
    if value is None:
        return
    return datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone.utc).strftime(
        '%Y-%m-%dT%H:%M:%S.%fZ')


class SimklEntry:
    def __init__(self, entry, source_type, identifiers):
        self.entry = entry
        self.source_type = source_type
        self.identifiers = identifiers

    @property
    def item_type(self):
        return 'movie' if self.source_type == 'movies' or self.entry.get('anime_type') == 'movie' else 'show'

    @property
    def title(self):
        return self.entry.get('movie') or self.entry['show']

    def get_base(self):
        tmdb_id = (
            self.identifiers.get_anime_movie_id(self.title)
            if self.source_type == 'anime' and self.item_type == 'movie' else
            self.identifiers.get_tmdb_id(self.title, self.item_type))
        if not tmdb_id:
            kodi_log(f'SIMKL: no TMDb {self.item_type} mapping for {self.title["ids"]["simkl"]}', 2)
            return
        return {
            'item_type': self.item_type, 'tmdb_id': tmdb_id,
            'title': self.title['title'], 'year': self.title.get('year'),
            'runtime': self.title.get('runtime'),
        }

    def get_episode(self, season, episode):
        if self.source_type == 'anime':
            # Missing cross-maps are an expected catalog limitation. Never use
            # AniDB/absolute numbers as if they were TMDb season coordinates.
            mapping = episode.get('tvdb')
            if not mapping:
                return
            season_number, episode_number = mapping['season'], mapping['episode']
        else:
            season_number, episode_number = season['number'], episode['number']
        return {
            'season_number': try_int(season_number), 'episode_number': try_int(episode_number),
            'last_watched_at': utc_timestamp(episode.get('watched_at')),
            'plays': 1 if episode.get('watched_at') else 0,
        }

    def get_episodes(self):
        return [item for item in (
            self.get_episode(season, episode)
            for season in self.entry.get('seasons', [])
            for episode in season.get('episodes', [])) if item is not None]

    def get_next(self):
        marker = self.entry.get('next_to_watch')
        if not marker or self.entry['status'] != 'watching':
            return
        match = fullmatch(r'S(\d+)E(\d+)', marker)
        if self.source_type != 'anime':
            if match is None:
                kodi_log(f'SIMKL: unrecognised next episode {marker!r} for {self.title["ids"].get("simkl")}', 2)
                return
            return tuple(int(value) for value in match.groups())
        # Native anime next markers cannot be assumed to use TMDb numbering.
        # Find the corresponding cross-map in the supplied episode rows.
        match = fullmatch(r'(?:S\d+)?E(\d+)', marker)
        if match is None:
            return
        number = int(match.group(1))
        mappings = (
            self.get_episode(season, episode)
            for season in self.entry.get('seasons', [])
            for episode in season.get('episodes', []) if episode['number'] == number)
        mapped = next((item for item in mappings if item is not None), None)
        if mapped is not None:
            return mapped['season_number'], mapped['episode_number']

    def get_item(self):
        base = self.get_base()
        if base is None:
            return
        episodes = self.get_episodes() if self.item_type == 'show' else []
        next_episode = self.get_next() if self.item_type == 'show' else None
        return dict(base, **{
            'status': self.entry['status'], 'episodes': episodes,
            'listed_at': utc_timestamp(self.entry.get('added_to_watchlist_at') or self.entry.get('first_seen_at')),
            'last_watched_at': utc_timestamp(self.entry.get('last_watched_at')),
            'watched_episodes': try_int(self.entry.get('watched_episodes_count')),
            'aired_episodes': max(0, try_int(self.entry.get('total_episodes_count'))
                - try_int(self.entry.get('not_aired_episodes_count'))),
            'next': next_episode,
            'next_episode_aired_at': utc_timestamp((self.entry.get('next_to_watch_info') or {}).get('date')),
            'source_type': self.source_type,
            'source_seasons': self.entry.get('mapped_tvdb_seasons') or [],
        })


class SimklLibraryMapping:
    def __init__(self, entries, identifiers=None):
        self.entries = entries
        self.identifiers = identifiers if identifiers is not None else SimklIdentifiers()

    def get_items(self):
        entries = (
            self.get_item(entry, source_type)
            for source_type, entries in self.entries.items() for entry in entries.values())
        items = {}
        for item in entries:
            if item is None:
                continue
            key = (item['item_type'], item['tmdb_id'])
            items[key] = self.merge(items[key], item) if key in items else item
        return list(items.values())

    def get_item(self, entry, source_type):
        # One malformed title must not stop the rest of the library from syncing.
        try:
            return SimklEntry(entry, source_type, self.identifiers).get_item()
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            simkl_id = ((entry.get('movie') or entry.get('show') or {}).get('ids') or {}).get('simkl')                 if isinstance(entry, dict) else None
            kodi_log(f'SIMKL: skipped malformed {source_type} entry {simkl_id}: {exc!r}', 2)

    @staticmethod
    def merge(previous, current):
        episodes = {}
        for episode in (*previous['episodes'], *current['episodes']):
            key = (episode['season_number'], episode['episode_number'])
            old = episodes.get(key)
            if old is None or (episode['last_watched_at'] or '') > (old['last_watched_at'] or ''):
                episodes[key] = episode
        next_item = min(
            (item for item in (previous, current) if item['next']),
            key=lambda item: item['next'], default=None)
        next_episode = next_item['next'] if next_item else None
        newest = max((previous, current), key=lambda item: item['last_watched_at'] or '')
        disjoint = (
            previous['source_type'] == current['source_type'] == 'anime'
            and previous['source_seasons'] and current['source_seasons']
            and set(previous['source_seasons']).isdisjoint(current['source_seasons']))
        aggregate = sum if disjoint else max
        return dict(newest, **{
            'episodes': list(episodes.values()), 'next': next_episode,
            'next_episode_aired_at': next_item['next_episode_aired_at'] if next_item else None,
            'watched_episodes': aggregate((previous['watched_episodes'], current['watched_episodes'])),
            'aired_episodes': aggregate((previous['aired_episodes'], current['aired_episodes'])),
            'listed_at': latest((previous['listed_at'], current['listed_at'])),
            'last_watched_at': latest((previous['last_watched_at'], current['last_watched_at'])),
            'status': 'watching' if next_episode else newest['status'],
            'source_seasons': sorted(set((*previous['source_seasons'], *current['source_seasons']))),
        })


class SimklWatchedMapping:
    def get_records(self, item):
        if item['item_type'] == 'movie':
            return [dict(item, plays=1 if item['last_watched_at'] or item['status'] == 'completed' else 0)]
        episodes = [dict(item, **episode, item_type='episode') for episode in item['episodes']]
        seasons = {}
        for episode in episodes:
            number = episode['season_number']
            seasons.setdefault(number, []).append(episode)
        return [dict(item, plays=0), *[
            dict(item, item_type='season', season_number=number,
                watched_episodes=sum(bool(episode['plays']) for episode in entries), plays=0,
                last_watched_at=latest(episode['last_watched_at'] for episode in entries))
            for number, entries in seasons.items()
        ], *episodes]
