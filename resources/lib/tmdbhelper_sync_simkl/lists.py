from time import time
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
            data = self.api.request(path, params={'limit': 500, 'page': page})
            items.extend(data[key])
            pagination = data['pagination']
            if pagination['page'] != page:
                raise ValueError('SIMKL returned a different list page')
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
            data = self.api.request(f'lists/{list_id}', params={'page': page, 'limit': self.page_size})
            if data['pagination']['page'] != page:
                raise ValueError('SIMKL returned a different list page')
            # Auto lists rebuild without activity bumps. Revisit them once per
            # day; regular owned lists use their updated_at revision as well.
            lifetime = 86400 if data['type'] == 'auto' or metadata is None else 180 * 86400
            self.api.store.set(key, {'revision': revision, 'expires': time() + lifetime, 'data': data})
            return data

    def get_media_item(self, item):
        item_type = 'movie' if item['type'] == 'movie' or item.get('anime_type') == 'movie' else 'show'
        tmdb_id = (
            self.identifiers.get_anime_movie_id(item)
            if item['type'] == 'anime' and item_type == 'movie' else
            self.identifiers.get_tmdb_id(item, item_type))
        if not tmdb_id:
            return
        return dict(item, item_type=item_type, tmdb_id=tmdb_id)
