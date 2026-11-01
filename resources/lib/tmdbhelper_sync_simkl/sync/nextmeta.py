from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.addon.tmdate import is_unaired_timestamp
from tmdbhelper.lib.items.database.baseview_factories.factory import BaseViewFactory


class SimklNextEpisodes:
    """Use the existing episode view for the list of remaining aired episodes."""

    def __init__(self, item):
        self.item = item

    @cached_property
    def watched(self):
        return self.get_watched()

    def get_watched(self):
        return frozenset(
            (episode['season_number'], episode['episode_number'])
            for episode in self.item['episodes'] if episode['plays'])

    def get_record(self, entry):
        season, episode = int(entry['params']['season']), int(entry['params']['episode'])
        if season <= 0 or (season, episode) in self.watched:
            return
        if is_unaired_timestamp(entry['infolabels'].get('premiered')):
            return
        return {
            'item_type': 'episode', 'tmdb_id': self.item['tmdb_id'], 'title': self.item['title'],
            'season_number': season, 'episode_number': episode,
            'upnext_episode_id': f'tv.{self.item["tmdb_id"]}.{season}.{episode}',
        }

    def get_records(self):
        view = BaseViewFactory('seasons', 'tv', self.item['tmdb_id'])
        return [record for season in view.data for record in self.get_season_records(season)]

    def get_season_records(self, season):
        number = int(season['params']['season'])
        if number <= 0:
            return []
        view = BaseViewFactory('episodes', 'tv', self.item['tmdb_id'], season=number)
        return [record for record in (self.get_record(entry) for entry in view.data) if record is not None]
