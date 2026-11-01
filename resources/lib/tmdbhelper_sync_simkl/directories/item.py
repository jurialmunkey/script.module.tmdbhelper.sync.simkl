from tmdbhelper.lib.items.directories.base.basedir_item import BaseDirItem


class SimklDirectoryItem(BaseDirItem):
    priority = 210
    label = 'SIMKL'
    params = {'info': 'simkl_userlists'}
    types = (None,)

    @property
    def enabled(self):
        from tmdbhelper_sync_simkl.settings import SimklSettings
        return bool(SimklSettings().client_id)
