from jurialmunkey.parser import try_int
from tmdbhelper_sync_simkl.sync.mapping import utc_timestamp


class SimklPlaybackMapping:
    def __init__(self, identifiers):
        self.identifiers = identifiers

    def get_item(self, entry):
        item_type = entry['type']
        title = entry['movie'] if item_type == 'movie' else entry['show']
        tmdb_id = self.identifiers.get_tmdb_id(title, 'movie' if item_type == 'movie' else 'show')
        if not tmdb_id:
            return
        item = {
            'item_type': item_type, 'tmdb_id': tmdb_id, 'title': title['title'], 'year': title.get('year'),
            'progress': entry['progress'], 'paused_at': utc_timestamp(entry['paused_at']), 'id': entry['id'],
        }
        if item_type == 'episode':
            episode = entry['episode']
            season = episode.get('tvdb_season', episode.get('season'))
            number = episode.get('tvdb_number', episode.get('number'))
            if season is None or number is None:
                return
            item.update(season_number=try_int(season), episode_number=try_int(number))
        return item

    def get_records(self, entries):
        return [item for item in (self.get_item(entry) for entry in entries) if item is not None]
