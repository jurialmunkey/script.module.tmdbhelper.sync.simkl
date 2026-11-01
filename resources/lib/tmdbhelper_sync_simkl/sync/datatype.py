from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper.lib.addon.tmdate import get_timestring_zulu_now, set_timestamp
from tmdbhelper.lib.sync.datatype import DataType
from tmdbhelper_sync_simkl.api import SimklAPIError
from tmdbhelper_sync_simkl.sync.itemdata import SimklSyncItem


class SimklDataType(DataType):
    expiry_time = 600

    def get_response_sync(self, *args, **kwargs):
        if not self.provider.is_authorized():
            return
        try:
            return self.get_records()
        except SimklAPIError as exc:
            kodi_log(str(exc), 1)

    def get_records(self):
        return []

    def get_syncitem(self, meta):
        item = SimklSyncItem(self.item_type, meta, self.keys, key_prefix=self.key_prefix)
        # Complete source mapping before the base pipeline clears any columns.
        item.data
        return item

    def store_last_activity(self):
        # Keep the remote watermark: changes during a slow request must not be
        # hidden by the base implementation's later local completion timestamp.
        self.cache.set_activity(
            self.item_type, self.cache_method, self.last_activity or get_timestring_zulu_now(),
            set_timestamp(self.expiry_time, set_int=True))
