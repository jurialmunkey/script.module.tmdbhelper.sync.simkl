from tmdbhelper.lib.sync.datatype import DataTypeEpisodesInShows
from tmdbhelper_sync_simkl.sync.datatype import SimklDataType
from tmdbhelper_sync_simkl.sync.mapping import SimklWatchedMapping


class SyncWatchlist(SimklDataType):
    keys = ('rank', 'listed_at', 'notes')
    key_prefix = 'watchlist'
    method = 'watchlist'
    last_activities_key = 'watchlisted_at'

    def get_records(self):
        if self.item_type not in ('movie', 'show'):
            return []
        return [dict(item, rank=rank) for rank, item in enumerate(self.provider.library_items, 1)
                if item['item_type'] == self.item_type and item['status'] == 'plantowatch']


class SyncWatched(DataTypeEpisodesInShows, SimklDataType):
    keys = ('plays', 'last_watched_at', 'watched_episodes')
    method = 'watched'
    last_activities_key = 'watched_at'

    def get_records(self):
        mapper = SimklWatchedMapping()
        return [record for item in self.provider.library_items
                if item['item_type'] == self.item_type for record in mapper.get_records(item)]


class SyncNextEpisodes(SimklDataType):
    keys = ('next_episode_id', 'next_episode_aired_at', 'aired_episodes')
    method = 'next_episodes'
    last_activities_key = 'watched_at'

    def get_records(self):
        if self.item_type != 'show':
            return []
        return [self.get_item(item) for item in self.provider.library_items if item['item_type'] == 'show']

    @staticmethod
    def get_item(item):
        next_episode = item['next']
        episode_id = f'tv.{item["tmdb_id"]}.{next_episode[0]}.{next_episode[1]}' if next_episode else None
        return dict(item, next_episode_id=episode_id)


class SyncAiredEpisodes(SyncNextEpisodes):
    keys = ('aired_episodes',)
    method = 'aired_episodes'


class SyncHiddenDropped(SimklDataType):
    keys = ('hidden_at',)
    key_prefix = 'dropped'
    method = 'dropped'
    last_activities_key = 'watched_at'

    def get_records(self):
        if self.item_type != 'show':
            return []
        return [dict(item, hidden_at=item['last_watched_at'] or item['listed_at'] or '1970-01-01T00:00:00Z')
                for item in self.provider.library_items
                if item['item_type'] == 'show' and item['status'] in ('dropped', 'hold')]


class SyncPlayback(DataTypeEpisodesInShows, SimklDataType):
    keys = ('progress', 'paused_at', 'id')
    key_prefix = 'playback'
    method = 'playback'
    last_activities_key = 'paused_at'

    def get_records(self):
        from tmdbhelper_sync_simkl.sync.playback import SimklPlaybackMapping
        return SimklPlaybackMapping(self.provider.identifiers).get_records(
            self.provider.library.get_playback(self.item_type))


class SyncAllNextEpisodes(DataTypeEpisodesInShows, SimklDataType):
    keys = ('upnext_episode_id',)
    method = 'all_next_episodes'
    last_activities_key = 'watched_at'

    def get_records(self):
        if self.item_type == 'movie':
            return []
        from tmdbhelper_sync_simkl.sync.nextmeta import SimklNextEpisodes
        return [record for item in self.provider.library_items
                if item['item_type'] == 'show' and item['next']
                for record in SimklNextEpisodes(item).get_records()]
