from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.sync.itemdata import SyncItem, SyncItemData


class SimklSyncItemData(SyncItemData):
    @cached_property
    def tmdb_id(self):
        return self.get_tmdb_id()

    def get_tmdb_id(self):
        return self.item['tmdb_id']

    @cached_property
    def season_number(self):
        return self.get_season_number()

    def get_season_number(self):
        return self.item.get('season_number')

    @cached_property
    def episode_number(self):
        return self.get_episode_number()

    def get_episode_number(self):
        return self.item.get('episode_number')

    def get_value(self, key):
        if key in ('item_type', 'tmdb_type', 'tmdb_id', 'season_number', 'episode_number'):
            return getattr(self, key)
        return self.item.get(key)


class SimklSyncItem(SyncItem):
    _additional_keys = (
        'item_type', 'tmdb_type', 'tmdb_id', 'season_number', 'episode_number', 'title', 'year',
    )

    def get_data(self):
        return {item.item_id: [item.get_value(key) for key in self.keys] for item in self.items}

    @cached_property
    def items(self):
        return self.get_items()

    def get_items(self):
        return [SimklSyncItemData(item, item['item_type']) for item in self.meta]
