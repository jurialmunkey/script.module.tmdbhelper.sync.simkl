from time import monotonic, time
from uuid import uuid4
from xbmc import Monitor
from xbmcgui import Dialog, DialogProgress
from tmdbhelper_sync_simkl.api import SimklAPIError


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
        if 'media:read' not in data['scope'].split():
            raise SimklAPIError('insufficient_scope')
        auth = {
            'client_id': self.settings.client_id,
            'session_id': previous['session_id'] if previous else uuid4().hex,
            'access_token': data['access_token'], 'refresh_token': data['refresh_token'],
            'expires_at': time() + data['expires_in'], 'scope': data['scope'],
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
            data = self.api.request('oauth2/token', data={
                'client_id': self.settings.client_id, 'grant_type': 'refresh_token',
                'refresh_token': auth['refresh_token'],
            }, authorized=False)
            return self.save_tokens(data, auth)

    def connect(self):
        if not self.settings.client_id:
            Dialog().ok('SIMKL', 'Enter your AUTH V2 client ID in this addon\'s settings first.')
            return False
        try:
            code = self.api.request('oauth2/device', data={
                'client_id': self.settings.client_id, 'scope': 'media:read',
            }, authorized=False)
            return self.poll(code)
        except SimklAPIError as exc:
            Dialog().ok('SIMKL', str(exc))
            return False

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
        if not self.is_authorized:
            self.settings.authorization = {}
            return
        try:
            self.api.request('oauth2/revoke', data={
                'client_id': self.settings.client_id,
                'token': self.settings.authorization['refresh_token'],
            }, authorized=False)
        except SimklAPIError as exc:
            Dialog().ok('SIMKL', f'{exc}\nYou can also revoke access in SIMKL Connected Apps.')
        self.settings.authorization = {}
