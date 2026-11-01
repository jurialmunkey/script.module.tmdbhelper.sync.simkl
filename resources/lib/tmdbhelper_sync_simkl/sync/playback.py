from jurialmunkey.parser import try_int
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper_sync_simkl.sync.mapping import utc_timestamp


class SimklPlaybackMapping:
    def __init__(self, identifiers, anime_ids=()):
        self.identifiers = identifiers
        # SIMKL IDs of titles in the anime library snapshot. Playback rows do not
        # say whether a title is anime, so the snapshot decides.
        self.anime_ids = frozenset(str(simkl_id) for simkl_id in anime_ids)

    def is_anime(self, title):
        return str(title['ids'].get('simkl')) in self.anime_ids or title.get('type') == 'anime'

    def get_tmdb_id(self, title, item_type, is_anime):
        if item_type == 'movie' and is_anime:
            # Anime film cross-references can point at the parent TV show.
            return self.identifiers.get_anime_movie_id(title)
        return self.identifiers.get_tmdb_id(title, 'movie' if item_type == 'movie' else 'show')

    @staticmethod
    def get_episode_numbers(episode, is_anime):
        if is_anime:
            # Only TVDB cross-maps are TMDb-compatible. Never use the native
            # (absolute/AniDB) numbers as season and episode coordinates.
            mapping = episode.get('tvdb') or {}
            season = episode.get('tvdb_season', mapping.get('season'))
            number = episode.get('tvdb_number', mapping.get('episode'))
        else:
            season = episode.get('tvdb_season', episode.get('season'))
            number = episode.get('tvdb_number', episode.get('number'))
        return season, number

    def get_item(self, entry):
        item_type = entry['type']
        title = entry['movie'] if item_type == 'movie' else entry['show']
        is_anime = self.is_anime(title)
        tmdb_id = self.get_tmdb_id(title, item_type, is_anime)
        if not tmdb_id:
            return
        item = {
            'item_type': item_type, 'tmdb_id': tmdb_id, 'title': title['title'], 'year': title.get('year'),
            'progress': entry['progress'], 'paused_at': utc_timestamp(entry['paused_at']), 'id': entry['id'],
        }
        if item_type == 'episode':
            season, number = self.get_episode_numbers(entry['episode'], is_anime)
            if season is None or number is None:
                return
            item.update(season_number=try_int(season), episode_number=try_int(number))
        return item

    def get_records(self, entries):
        records = []
        for entry in entries:
            try:
                item = self.get_item(entry)
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                kodi_log(f'SIMKL: skipped malformed playback entry {entry.get("id") if isinstance(entry, dict) else None}: {exc!r}', 2)
                continue
            if item is not None:
                records.append(item)
        return records
