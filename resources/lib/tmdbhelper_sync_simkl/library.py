from copy import deepcopy
from xbmc import Monitor
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.addon.tmdate import get_timestring_zulu_now
from tmdbhelper_sync_simkl.api import SimklAPIError


class SimklLibrary:
    """Merge API deltas into a complete source snapshot before core sync reads it."""

    source_types = {'shows': 'tv_shows', 'movies': 'movies', 'anime': 'anime'}
    statuses = ('watching', 'plantowatch', 'hold', 'completed', 'dropped')

    def __init__(self, api):
        self.api = api

    @staticmethod
    def identity(entry):
        title = entry.get('movie') or entry['show']
        return str(title['ids']['simkl'])

    def fetch(self, source_type, date_from=None, ids_only=False, status=None):
        params = {'extended': 'simkl_ids_only' if ids_only else (
            'full_anime_seasons' if source_type == 'anime' else 'full')}
        if not ids_only:
            params.update({
                'episode_watched_at': 'yes', 'include_all_episodes': 'yes',
                'next_watch_info': 'yes', 'episode_tvdb_id': 'yes',
            })
        if date_from is not None:
            params['date_from'] = date_from
        path = f'sync/all-items/{source_type}'
        if status is not None:
            path = f'{path}/{status}'
        try:
            data = self.api.request(path, params=params)
        except SimklAPIError as exc:
            if exc.code != 'max_items' or status is not None:
                raise
            return self.fetch_by_status(source_type, date_from, ids_only)
        # An account with nothing in this bucket may return an empty body or null.
        if not data:
            return {}
        if not isinstance(data, dict) or not isinstance(data.get(source_type) or [], list):
            raise SimklAPIError('invalid_response')
        entries = {}
        for entry in data.get(source_type) or []:
            try:
                entries[self.identity(entry)] = entry
            except (KeyError, TypeError):
                kodi_log('SIMKL: skipped an item without a SIMKL ID', 2)
        return entries

    def fetch_by_status(self, source_type, date_from, ids_only):
        statuses = self.statuses if source_type != 'movies' else ('plantowatch', 'completed', 'dropped')
        entries = {}
        for status in statuses:
            self.check_abort()
            entries.update(self.fetch(source_type, date_from, ids_only, status))
        return entries

    @staticmethod
    def check_abort():
        if Monitor().abortRequested():
            raise SimklAPIError('request_aborted')

    def merge_entries(self, previous, updates):
        for key, item in updates.items():
            item['first_seen_at'] = previous.get(key, {}).get('first_seen_at') or get_timestring_zulu_now()
        return dict(previous, **updates)

    def update_type(self, source_type, previous, current, entries):
        bucket = self.source_types[source_type]
        old = previous.get(bucket) or {}
        new = current.get(bucket) or {}
        if any(old.get(key) != new.get(key) for key in self.statuses):
            entries = self.merge_entries(entries, self.fetch(source_type, date_from=previous['all']))
        if old.get('removed_from_list') != new.get('removed_from_list'):
            ids = self.fetch(source_type, ids_only=True)
            return {key: value for key, value in entries.items() if key in ids}
        return entries

    def get_entries(self):
        return self.get_snapshot()['entries']

    def get_snapshot(self):
        """Return the current {'activity', 'entries'} snapshot, updating it first if needed."""
        with self.api.store.lock('library') as lock:
            if lock.lockstate == -1:
                raise SimklAPIError('request_aborted')
            activity = self.api.get_activities()
            previous = self.api.store.get('library')
            if previous is not None and previous['activity'] == activity:
                return previous
            entries = deepcopy(previous['entries']) if previous is not None else {}
            for source_type in self.source_types:
                self.check_abort()
                entries[source_type] = (
                    self.merge_entries({}, self.fetch(source_type)) if previous is None else
                    self.update_type(source_type, previous['activity'], activity, entries[source_type]))
            # Failed requests never advance the snapshot or replace cached entries.
            snapshot = {'activity': activity, 'entries': entries}
            self.api.store.set('library', snapshot)
            return snapshot

    def get_playback(self, item_type):
        source_type = 'movies' if item_type == 'movie' else 'episodes'
        with self.api.store.lock(f'playback.{source_type}') as lock:
            if lock.lockstate == -1:
                raise SimklAPIError('request_aborted')
            activities = self.api.get_activities()
            buckets = ('movies',) if item_type == 'movie' else ('tv_shows', 'anime')
            activity = [(activities.get(bucket) or {}).get('playback') for bucket in buckets]
            cached = self.api.store.get(f'playback.{source_type}')
            if cached is not None and cached['activity'] == activity:
                return cached['entries']
            entries = self.api.request(f'sync/playback/{source_type}', params={'limit': 10000}) or []
            if not isinstance(entries, list):
                raise SimklAPIError('invalid_response')
            self.api.store.set(f'playback.{source_type}', {'activity': activity, 'entries': entries})
            return entries
