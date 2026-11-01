from json import dumps
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.sync.providers.base import SyncProvider
from tmdbhelper_sync_simkl.api import SimklAPI, SimklAPIError
from tmdbhelper_sync_simkl.identifiers import SimklIdentifiers
from tmdbhelper_sync_simkl.library import SimklLibrary
from tmdbhelper_sync_simkl.sync import synctype
from tmdbhelper_sync_simkl.sync.datasync import SimklMoviesToWatch, SimklShowsToWatch, SimklShowsInProgress
from tmdbhelper_sync_simkl.sync.mapping import SimklLibraryMapping, latest
from tmdbhelper_sync_simkl.directories.item import SimklDirectoryItem
from tmdbhelper_sync_simkl.directories.routes import LIST_ROUTES


class Provider(SyncProvider):
    interface_version = 3
    provider_id = 'simkl'
    display_name = 'SIMKL'
    sync_classes = {
        'SyncWatchlist': synctype.SyncWatchlist,
        'SyncWatched': synctype.SyncWatched,
        'SyncPlayback': synctype.SyncPlayback,
        'SyncNextEpisodes': synctype.SyncNextEpisodes,
        'SyncAllNextEpisodes': synctype.SyncAllNextEpisodes,
        'SyncAiredEpisodes': synctype.SyncAiredEpisodes,
        'SyncHiddenDropped': synctype.SyncHiddenDropped,
    }
    getter_classes = {
        'movies_to_watch': SimklMoviesToWatch,
        'shows_to_watch': SimklShowsToWatch,
        'shows_in_progress': SimklShowsInProgress,
    }
    directory_item_class = SimklDirectoryItem
    list_routes = LIST_ROUTES

    @cached_property
    def api(self):
        return self.get_api()

    def get_api(self):
        return SimklAPI()

    @cached_property
    def identifiers(self):
        return SimklIdentifiers()

    @cached_property
    def library(self):
        return self.get_library()

    def get_library(self):
        return SimklLibrary(self.api)

    _library_items = None

    @property
    def library_items(self):
        # A provider can outlive one sync (e.g. the post-playback refresh), so
        # re-map whenever the stored snapshot's activity changes.
        snapshot = self.library.get_snapshot()
        key = dumps(snapshot['activity'], sort_keys=True)
        if self._library_items is None or self._library_items[0] != key:
            self._library_items = (key, self.get_library_items(snapshot['entries']))
        return self._library_items[1]

    def get_library_items(self, entries):
        return SimklLibraryMapping(entries, self.identifiers).get_items()

    @cached_property
    def user_lists(self):
        return self.get_user_lists()

    def get_user_lists(self):
        from tmdbhelper_sync_simkl.lists import SimklUserLists
        return SimklUserLists(self.api, self.identifiers)

    def is_authorized(self):
        return self.api.auth.is_authorized

    def get_last_activities(self):
        if not self.is_authorized():
            return
        try:
            return self.map_activities(self.api.get_activities())
        except SimklAPIError as exc:
            kodi_log(str(exc), 1)

    @staticmethod
    def map_activities(data):
        television = (data.get('tv_shows') or {}, data.get('anime') or {})
        return {
            item_type: {
                'watchlisted_at': latest(
                    bucket.get(key) for bucket in buckets for key in ('plantowatch', 'removed_from_list')),
                'watched_at': latest(
                    bucket.get(key) for bucket in buckets
                    for key in (*SimklLibrary.statuses, 'removed_from_list')),
                'paused_at': latest(bucket.get('playback') for bucket in buckets),
            }
            for item_type, buckets in (
                ('movies', (data.get('movies') or {}, data.get('anime') or {})),
                ('shows', television), ('seasons', television), ('episodes', television))
        }
