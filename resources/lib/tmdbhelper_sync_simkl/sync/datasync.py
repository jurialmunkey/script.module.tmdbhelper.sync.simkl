from tmdbhelper.lib.sync.datasync import (
    SyncDataGetterAllMoviesToWatch,
    SyncDataGetterAllShowsToWatch,
    SyncDataGetterAllUnHiddenShowsNextEpisode,
)


class SimklMoviesToWatch(SyncDataGetterAllMoviesToWatch):
    pass


class SimklShowsToWatch(SyncDataGetterAllShowsToWatch):
    query_clauses = ('item_type=?', 'dropped_hidden_at IS NULL')
    filter_keys = ('dropped_hidden_at',)


class SimklShowsInProgress(SyncDataGetterAllUnHiddenShowsNextEpisode):
    # SiMKL's next_to_watch is authoritative, including caught-up shows. Episode
    # counts can be stale and must not keep finished shows in progress lists.
    query_clauses = ('item_type=?', 'dropped_hidden_at IS NULL')
