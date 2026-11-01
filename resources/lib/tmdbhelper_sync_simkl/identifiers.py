from jurialmunkey.ftools import cached_property
from jurialmunkey.parser import try_int


class SimklIdentifiers:
    """Resolve external IDs through the existing query interface, never by title."""

    @cached_property
    def query_database(self):
        return self.get_query_database()

    def get_query_database(self):
        from tmdbhelper.lib.query.database.database import FindQueriesDatabase
        return FindQueriesDatabase()

    def get_tmdb_id(self, title, item_type):
        ids = title['ids']
        if try_int(ids.get('tmdb')):
            return try_int(ids['tmdb'])
        return self.query_database.get_tmdb_id(
            tmdb_type='movie' if item_type == 'movie' else 'tv',
            imdb_id=ids.get('imdb'), tvdb_id=ids.get('tvdb'))

    def get_anime_movie_id(self, title):
        # Anime movie cross-references can point at the parent TV show. Resolve
        # the movie's IMDb ID instead of interpreting that TV ID as a film ID.
        return self.query_database.get_tmdb_id(tmdb_type='movie', imdb_id=title['ids'].get('imdb'))
