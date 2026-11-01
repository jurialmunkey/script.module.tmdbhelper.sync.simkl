from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.items.directories.mapper_basic import ItemMapper


def poster_url(path):
    if not path or path.startswith('https://'):
        return path
    return f'https://wsrv.nl/?url=https://simkl.in/posters/{path}_m.webp&q=90'


class SimklUserListMapper(ItemMapper):
    @cached_property
    def label(self):
        return self.get_label()

    def get_label(self):
        return self.meta['name']

    def get_infolabels(self):
        description = self.meta['description']
        return {'plot': description.get('full') or description.get('short')}

    def get_infoproperties(self):
        return {
            'items': self.meta['counts']['items'], 'privacy': self.meta['privacy'],
            'list_type': self.meta['type'], 'updated_at': self.meta['updated_at'],
        }

    def get_art(self):
        preview = self.meta.get('top_items') or []
        return {'icon': poster_url(preview[0]['poster']) if preview else 'DefaultFolder.png'}

    def get_params(self):
        return {
            'info': 'simkl_userlist', 'list_id': self.meta['id'], 'tmdb_type': 'both',
            'list_name': self.label, 'plugin_category': self.label,
        }

    def get_unique_ids(self):
        return {'list_id': self.meta['id'], 'user_id': self.meta['user']['id']}


class SimklMediaMapper(ItemMapper):
    @cached_property
    def label(self):
        return self.get_label()

    def get_label(self):
        return self.meta['title']

    def get_infolabels(self):
        return {
            'title': self.label, 'year': self.meta.get('year'), 'plot': self.meta.get('overview'),
            'mediatype': 'movie' if self.meta['item_type'] == 'movie' else 'tvshow',
        }

    def get_infoproperties(self):
        return {'rank': self.meta.get('position')}

    def get_unique_ids(self):
        return dict(self.meta['ids'], tmdb=self.meta['tmdb_id'])

    def get_params(self):
        return {
            'info': 'details', 'tmdb_type': 'movie' if self.meta['item_type'] == 'movie' else 'tv',
            'tmdb_id': self.meta['tmdb_id'],
        }

    def get_art(self):
        return {'poster': poster_url(self.meta.get('poster')), 'icon': poster_url(self.meta.get('poster'))}


class SimklMessageMapper(ItemMapper):
    @cached_property
    def label(self):
        return self.get_label()

    def get_label(self):
        return self.meta['message']

    def get_infolabels(self):
        return {'plot': self.label}

    def get_item(self):
        return dict(super().get_item(), is_folder=False)
