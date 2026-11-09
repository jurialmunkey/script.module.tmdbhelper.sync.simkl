from json import dumps, loads
from xbmcaddon import Addon
from xbmcvfs import translatePath
from tmdbhelper_sync_simkl.keys import CLIENT_ID


class SimklSettings:
    addon_id = 'script.module.tmdbhelper.sync.simkl'
    client_id = CLIENT_ID

    def __init__(self):
        self.addon = Addon(self.addon_id)

    @property
    def version(self):
        return self.addon.getAddonInfo('version')

    @property
    def profile(self):
        return translatePath(self.addon.getAddonInfo('profile'))

    @property
    def authorization(self):
        return loads(self.addon.getSetting('authorization') or '{}')

    @authorization.setter
    def authorization(self, value):
        self.addon.setSetting('authorization', dumps(value))

    @property
    def account_key(self):
        session_id = self.authorization.get('session_id')
        if not session_id:
            from tmdbhelper_sync_simkl.errors import SimklAPIError
            raise SimklAPIError('authorization_required')
        return f'{self.client_id}.{session_id}'
