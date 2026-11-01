from jurialmunkey.parser import try_int
from tmdbhelper.lib.items.directories.lists_default import ListDefault, ListProperties
from tmdbhelper.lib.sync.providers.registry import SyncProviderRegistry
from tmdbhelper_sync_simkl.api import SimklAPIError
from tmdbhelper_sync_simkl.directories.mapper import SimklUserListMapper, SimklMediaMapper, SimklMessageMapper


class SimklListProperties(ListProperties):
    plugin_name = 'SIMKL - Your Lists'
    container_content = ''
    item_mapper_class = SimklUserListMapper
    page_size = 20

    @property
    def next_page(self):
        return self.page + 1

    def get_cached_items(self, *args, **kwargs):
        # The account-aware provider client caches source pages and revisions.
        return self.get_uncached_items()

    def get_uncached_items(self):
        if not self.provider.is_authorized():
            return self.get_message('Connect your SIMKL account in the provider addon settings.')
        try:
            return self.get_page()
        except SimklAPIError as exc:
            if exc.code == 'premium_only':
                return self.get_message('SIMKL custom lists require a PRO or VIP account.')
            return self.get_message(str(exc))

    def get_message(self, message):
        return {'items': [SimklMessageMapper({'message': message}, None).item], 'pages': 0, 'count': 0}

    def get_page(self):
        entries = self.provider.user_lists.get_lists()
        start = (self.page - 1) * self.page_size
        return {
            'items': [self.get_mapped_item(item) for item in entries[start:start + self.page_size]],
            'pages': (len(entries) + self.page_size - 1) // self.page_size, 'count': len(entries),
        }

    def get_mapped_item(self, item, add_infoproperties=None):
        return self.item_mapper_class(item, add_infoproperties).item


class SimklListItemsProperties(SimklListProperties):
    plugin_name = 'SIMKL'
    container_content = 'videos'
    item_mapper_class = SimklMediaMapper

    def get_page(self):
        client = self.provider.user_lists
        data = client.get_list_page(self.list_id, self.page)
        entries = [item for item in (client.get_media_item(item) for item in data['items']) if item is not None]
        pagination = data['pagination']
        return {
            'items': [self.get_mapped_item(item) for item in entries],
            'pages': min(pagination['total_pages'], 10000 // client.page_size),
            'count': pagination['total_items'],
        }


class ListSimklUserLists(ListDefault):
    list_properties_class = SimklListProperties
    kodi_details = False

    def configure_list_properties(self, list_properties):
        list_properties = super().configure_list_properties(list_properties)
        list_properties.provider = SyncProviderRegistry().get_provider('simkl')
        list_properties.plugin_name = 'SIMKL - Your Lists'
        list_properties.pagination = True
        return list_properties

    def get_items(self, page=1, **kwargs):
        self.list_properties.page = max(1, try_int(page))
        return self.get_items_finalised()


class ListSimklUserList(ListSimklUserLists):
    list_properties_class = SimklListItemsProperties
    kodi_details = True

    def get_items(self, list_id, list_name=None, **kwargs):
        self.list_properties.list_id = str(int(list_id))
        self.list_properties.plugin_name = list_name or 'SIMKL'
        return super().get_items(**kwargs)
