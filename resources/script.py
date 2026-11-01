from os.path import join
from sys import argv, path
from xbmc import executebuiltin
from xbmcaddon import Addon


def configure():
    executebuiltin(
        'RunScript(plugin.video.themoviedb.helper,configure_sync_provider,'
        'addon_id=script.module.tmdbhelper.sync.simkl)')


def main():
    addon = Addon('script.module.tmdbhelper.sync.simkl')
    path.insert(0, join(Addon('plugin.video.themoviedb.helper').getAddonInfo('path'), 'resources'))
    from tmdbhelper.lib.sync.providers.loader import SyncProviderLoader
    module = SyncProviderLoader({
        'addonid': addon.getAddonInfo('id'), 'path': addon.getAddonInfo('path'),
    }).load_module()
    api = module.Provider().api
    action = argv[1] if len(argv) > 1 else 'configure'
    if action == 'disconnect':
        api.auth.disconnect()
        invalidate_sync(module.Provider())
    elif action == 'connect':
        if api.auth.connect():
            invalidate_sync(module.Provider())
            configure()
    elif api.auth.is_authorized:
        configure()
    else:
        addon.openSettings()


def invalidate_sync(provider):
    from tmdbhelper.lib.sync.invalidator import SyncInvalidatorAll
    SyncInvalidatorAll().invalidate_provider(provider)


if __name__ == '__main__':
    main()
