from contextlib import closing
from json import dumps, loads
from os import makedirs
from os.path import join
from sqlite3 import connect
from tmdbhelper.lib.files.sqlite_mutex import SQLiteMutex


class SimklStore:
    """Provider-owned source snapshots, separate from the item-details cache."""

    def __init__(self, settings):
        self.settings = settings
        makedirs(settings.profile, exist_ok=True)
        self.path = join(settings.profile, 'state.db')
        with closing(connect(self.path)) as connection:
            connection.execute('CREATE TABLE IF NOT EXISTS state (id TEXT PRIMARY KEY, data TEXT NOT NULL)')
            connection.commit()

    def lock(self, name):
        return SQLiteMutex(f'{self.path}.{name}', timeout=300)

    def get(self, key):
        with closing(connect(self.path)) as connection:
            row = connection.execute('SELECT data FROM state WHERE id=?', (self.key(key),)).fetchone()
        return loads(row[0]) if row is not None else None

    def set(self, key, value):
        with closing(connect(self.path)) as connection:
            connection.execute(
                'INSERT OR REPLACE INTO state (id, data) VALUES (?, ?)',
                (self.key(key), dumps(value)))
            connection.commit()

    def key(self, name):
        return f'{self.settings.account_key}.{name}'

    def prune(self):
        """Delete snapshots that belong to any authorization other than the current one."""
        prefix = f'{self.settings.account_key}.'
        with closing(connect(self.path)) as connection:
            connection.execute('DELETE FROM state WHERE substr(id, 1, ?) != ?', (len(prefix), prefix))
            connection.commit()

    def clear(self):
        with closing(connect(self.path)) as connection:
            connection.execute('DELETE FROM state')
            connection.commit()
