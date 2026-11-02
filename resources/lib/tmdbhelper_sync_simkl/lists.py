from time import time
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper_sync_simkl.api import SimklAPIError


class SimklUserLists:
    page_size = 50

    def __init__(self, api, identifiers):
        self.api = api
        self.identifiers = identifiers

    def get_lists(self):
        with self.api.store.lock('user_lists') as lock:
            if lock.lockstate == -1:
                raise SimklAPIError('request_aborted')
            activity = self.api.get_activities().get('custom_lists', {}).get('lists', {}).get('all')
            cached = self.api.store.get('user_lists')
            if cached is not None and cached['activity'] == activity:
                return cached['lists']
            profile = self.api.get_profile()
            user_id = profile['account']['id']
            lists = self.get_all_pages(f'lists/user/{user_id}', 'lists')
            self.api.store.set('user_lists', {'activity': activity, 'lists': lists})
            return lists

    def get_all_pages(self, path, key):
        items = []
        page = 1
        while True:
            data = self.api.request_dict(path, key, 'pagination', params={'limit': 500, 'page': page})
            pagination = self.get_pagination(data, page)
            items.extend(data[key] or [])
            if page >= pagination['total_pages']:
                return items
            page += 1
            if page * 500 > 10000:
                raise SimklAPIError('pagination_limit')

    def get_list_page(self, list_id, page):
        lists = self.get_lists()
        metadata = next((item for item in lists if str(item['id']) == str(list_id)), None)
        revision = metadata['updated_at'] if metadata else None
        with self.api.store.lock(f'list.{list_id}') as lock:
            if lock.lockstate == -1:
                raise SimklAPIError('request_aborted')
            key = f'list.{list_id}.{page}'
            cached = self.api.store.get(key)
            if cached is not None and cached['revision'] == revision and cached['expires'] > time():
                return cached['data']
            if page < 1 or page * self.page_size > 10000:
                raise SimklAPIError('pagination_limit')
            data = self.api.request_dict(
                f'lists/{list_id}', 'items', 'pagination', 'type', params={'page': page, 'limit': self.page_size})
            self.get_pagination(data, page)
            # Auto lists rebuild without activity bumps. Revisit them once per
            # day; regular owned lists use their updated_at revision as well.
            lifetime = 86400 if data['type'] == 'auto' or metadata is None else 180 * 86400
            self.api.store.set(key, {'revision': revision, 'expires': time() + lifetime, 'data': data})
            return data

    @staticmethod
    def get_pagination(data, page):
        pagination = data['pagination']
        if (
                not isinstance(pagination, dict) or pagination.get('page') != page
                or not isinstance(pagination.get('total_pages'), int)):
            raise SimklAPIError('invalid_response')
        return pagination

    def get_media_item(self, item):
        try:
            return self.map_media_item(item)
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            kodi_log(f'SIMKL: skipped malformed list item: {exc!r}', 2)

    def map_media_item(self, item):
        item_type = 'movie' if item['type'] == 'movie' or item.get('anime_type') == 'movie' else 'show'
        tmdb_id = (
            self.identifiers.get_anime_movie_id(item)
            if item['type'] == 'anime' and item_type == 'movie' else
            self.identifiers.get_tmdb_id(item, item_type))
        if not tmdb_id:
            return
        return dict(item, item_type=item_type, tmdb_id=tmdb_id)
