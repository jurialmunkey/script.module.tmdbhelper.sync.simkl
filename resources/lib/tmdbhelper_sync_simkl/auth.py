from time import monotonic, time
from uuid import uuid4
from xbmc import Monitor
from xbmcgui import Dialog, DialogProgress
from jurialmunkey.parser import try_int
from tmdbhelper.lib.addon.logger import kodi_log
from tmdbhelper_sync_simkl.errors import SimklAPIError

SCOPE = 'media:read'
DEFAULT_EXPIRES_IN = 7 * 86400

# OAuth errors meaning the stored grant can never be refreshed again.
REVOKED_GRANT_ERRORS = ('invalid_grant', 'invalid_client', 'unauthorized_client', 'invalid_token')


class SimklAuthorization:
    def __init__(self, api):
        self.api = api
        self.settings = api.settings

    @property
    def is_authorized(self):
        auth = self.settings.authorization
        return bool(
            self.settings.client_id and auth.get('client_id') == self.settings.client_id
            and auth.get('access_token') and auth.get('refresh_token'))

    def get_access_token(self):
        if not self.is_authorized:
            return
        auth = self.settings.authorization
        if auth['expires_at'] <= time() + 60:
            return self.refresh(auth['access_token'])
        return auth['access_token']

    def save_tokens(self, data, previous=None):
        previous = previous or {}
        # Token responses may omit an unchanged scope or a non-rotated refresh token.
        scope = data.get('scope') or previous.get('scope') or SCOPE
        refresh_token = data.get('refresh_token') or previous.get('refresh_token')
        if not data.get('access_token') or not refresh_token:
            raise SimklAPIError('invalid_token_response')
        if SCOPE not in scope.split():
            raise SimklAPIError('insufficient_scope')
        auth = {
            'client_id': self.settings.client_id,
            'session_id': previous.get('session_id') or uuid4().hex,
            'access_token': data['access_token'], 'refresh_token': refresh_token,
            'expires_at': time() + (try_int(data.get('expires_in')) or DEFAULT_EXPIRES_IN), 'scope': scope,
        }
        self.settings.authorization = auth
        return auth['access_token']

    def refresh(self, old_token):
        with self.api.store.lock('authorization') as lock:
            if lock.lockstate == -1:
                raise SimklAPIError('request_aborted')
            if not self.is_authorized:
                raise SimklAPIError('authorization_required')
            auth = self.settings.authorization
            # Another Kodi process may already have refreshed this grant.
            if auth['access_token'] != old_token:
                return auth['access_token']
            try:
                data = self.api.request('oauth2/token', data={
                    'client_id': self.settings.client_id, 'grant_type': 'refresh_token',
                    'refresh_token': auth['refresh_token'],
                }, authorized=False)
            except SimklAPIError as exc:
                if exc.code not in REVOKED_GRANT_ERRORS:
                    raise
                # The grant is gone: stop retrying and show the account as disconnected.
                kodi_log('SIMKL authorization expired or was revoked. Reconnect the SIMKL account.', 1)
                self.api.store.clear()
                self.settings.authorization = {}
                raise SimklAPIError('authorization_required', exc.status) from None
            return self.save_tokens(data, auth)

    def connect(self):
        try:
            code = self.api.request('oauth2/device', data={
                'client_id': self.settings.client_id, 'scope': SCOPE,
            }, authorized=False)
            if not self.poll(code):
                return False
        except SimklAPIError as exc:
            Dialog().ok('SIMKL', str(exc))
            return False
        # Each authorization has its own namespace; drop snapshots from older ones.
        self.api.store.prune()
        return True

    def poll(self, code):
        monitor = Monitor()
        dialog = DialogProgress()
        duration = code['expires_in']
        deadline = monotonic() + duration
        interval = code['interval']
        next_poll = monotonic() + interval
        dialog.create('Connect SIMKL', f'Visit {code["verification_uri"]}\nEnter code: [B]{code["user_code"]}[/B]')
        try:
            while monotonic() < deadline:
                if dialog.iscanceled() or monitor.waitForAbort(0.2):
                    return False
                dialog.update(min(100, int(100 * (1 - (deadline - monotonic()) / duration))))
                if monotonic() < next_poll:
                    continue
                try:
                    data = self.api.request('oauth2/token', data={
                        'client_id': self.settings.client_id,
                        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                        'device_code': code['device_code'],
                    }, authorized=False)
                except SimklAPIError as exc:
                    if exc.code not in ('authorization_pending', 'slow_down'):
                        raise
                    interval += 5 if exc.code == 'slow_down' else 0
                    next_poll = monotonic() + interval
                    continue
                self.save_tokens(data)
                return True
        finally:
            dialog.close()
        Dialog().ok('SIMKL', 'The device code expired. Connect again to request a new code.')
        return False

    def disconnect(self):
        auth = self.settings.authorization
        # Revoke with the original client, including grants from before the bundled ID.
        if auth.get('refresh_token') and auth.get('client_id'):
            try:
                self.api.request('oauth2/revoke', data={
                    'client_id': auth['client_id'], 'token': auth['refresh_token'],
                }, authorized=False)
            except SimklAPIError as exc:
                Dialog().ok('SIMKL', f'{exc}\nYou can also revoke access in SIMKL Connected Apps.')
        self.api.store.clear()
        self.settings.authorization = {}
