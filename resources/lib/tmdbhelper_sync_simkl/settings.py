from json import dumps, loads
from xbmcaddon import Addon
from xbmcvfs import translatePath


class SimklSettings:
    addon_id = 'script.module.tmdbhelper.sync.simkl'

    def __init__(self):
        self.addon = Addon(self.addon_id)

    @property
    def client_id(self):
        return self.addon.getSetting('client_id').strip()

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
        auth = self.authorization
        return f'{self.client_id}.{auth["session_id"]}'
