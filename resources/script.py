from sys import argv
from xbmc import executebuiltin
from xbmcaddon import Addon

ADDON_ID = 'script.module.tmdbhelper.sync.simkl'


def configure():
    executebuiltin(
        'RunScript(plugin.video.themoviedb.helper,configure_sync_provider,'
        f'addon_id={ADDON_ID})')


def reopen_settings():
    # Settings buttons close (and save) the dialog before running this script.
    executebuiltin(f'Addon.OpenSettings({ADDON_ID})')


def main():
    addon = Addon(ADDON_ID)
    from tmdbhelper_lib.sync.providers.interface import SyncProviderLoader
    module = SyncProviderLoader({
        'addonid': addon.getAddonInfo('id'), 'path': addon.getAddonInfo('path'),
    }).load_module()
    provider = module.Provider()
    auth = provider.api.auth
    action = argv[1] if len(argv) > 1 else 'configure'
    if action == 'disconnect':
        auth.disconnect()
        invalidate_sync(provider)
        reopen_settings()
    elif action == 'connect':
        if not auth.connect():
            reopen_settings()
            return
        invalidate_sync(provider)
        configure()
    elif auth.is_authorized:
        configure()
    else:
        addon.openSettings()


def invalidate_sync(provider):
    from tmdbhelper_lib.sync.providers.interface import SyncInvalidatorAll
    SyncInvalidatorAll().invalidate_provider(provider)


if __name__ == '__main__':
    main()
