from email.utils import parsedate_to_datetime
from time import time
from urllib.parse import urlencode
from jurialmunkey.ftools import cached_property
from tmdbhelper.lib.api.request import NoCacheRequestAPI
from tmdbhelper_sync_simkl.errors import SimklAPIError  # noqa: F401 (re-exported)
from tmdbhelper_sync_simkl.settings import SimklSettings
from tmdbhelper_sync_simkl.store import SimklStore

DEFAULT_RETRY_AFTER = 60


def get_retry_after(value):
    """Seconds to wait from a Retry-After header: delay-seconds or an HTTP date."""
    if not value:
        return DEFAULT_RETRY_AFTER
    try:
        return max(0, int(value))
    except ValueError:
        pass
    try:
        return max(0, int(parsedate_to_datetime(value).timestamp() - time()))
    except (TypeError, ValueError, OverflowError):
        return DEFAULT_RETRY_AFTER


class SimklAPI(NoCacheRequestAPI):
    app_name = 'tmdbhelper-sync-simkl'

    def __init__(self):
        self.settings = SimklSettings()
        super().__init__(req_api_url='https://api.simkl.com', req_api_name='SIMKL')

    @cached_property
    def store(self):
        return SimklStore(self.settings)

    @cached_property
    def auth(self):
        from tmdbhelper_sync_simkl.auth import SimklAuthorization
        return SimklAuthorization(self)

    def request(self, path, params=None, data=None, authorized=True, retry=True):
        headers = {'User-Agent': f'{self.app_name}/{self.settings.version}'}
        token = self.auth.get_access_token() if authorized else None
        if authorized:
            if not token:
                raise SimklAPIError('authorization_required')
            headers['Authorization'] = f'Bearer {token}'
            cooldown = self.store.get('backoff') or 0
            if cooldown > time():
                raise SimklAPIError('rate_limit', 429)
        query = {
            'client_id': self.settings.client_id, 'app-name': self.app_name,
            'app-version': self.settings.version, **(params or {}),
        }
        url = f'{self.req_api_url}/{path}?{urlencode(query)}'
        # The shared HTTP error logger prints headers and POST data. Use its
        # transport only, then handle HTTP errors here without logging secrets.
        response = self.get_simple_api_request(
            url, postdata=data, headers=headers, method='post' if data is not None else None)
        if response is None:
            raise SimklAPIError('connection_failed')
        try:
            status = response.status_code
            if status == 429 and authorized:
                self.store.set('backoff', time() + get_retry_after(response.headers.get('Retry-After')))
            try:
                body = response.json() if response.content else {}
            except ValueError:
                raise SimklAPIError('invalid_json', status) from None
        finally:
            response.close()
        error = body.get('error') if isinstance(body, dict) else None
        if status == 401 and authorized and retry and error == 'user_token_failed':
            self.auth.refresh(token)
            return self.request(path, params, data, authorized=True, retry=False)
        if status >= 400 or error:
            raise SimklAPIError(error or 'request_failed', status)
        return body

    def request_dict(self, path, *keys, **kwargs):
        """Request a JSON object and check that it has the given keys."""
        data = self.request(path, **kwargs)
        if not isinstance(data, dict) or any(key not in data for key in keys):
            raise SimklAPIError('invalid_response')
        return data

    def get_activities(self):
        with self.store.lock('activities') as lock:
            if lock.lockstate == -1:
                raise SimklAPIError('request_aborted')
            cached = self.store.get('activities')
            if cached is not None and cached['expires'] > time():
                return cached['data']
            # Null is valid for an empty account; a missing key is not.
            data = self.request_dict('sync/activities', 'all')
            self.store.set('activities', {'data': data, 'expires': time() + 60})
            return data

    def get_profile(self):
        with self.store.lock('profile') as lock:
            if lock.lockstate == -1:
                raise SimklAPIError('request_aborted')
            cached = self.store.get('profile')
            activity = (self.get_activities().get('settings') or {}).get('all')
            if cached is not None and cached['activity'] == activity:
                return cached['data']
            data = self.request_dict('users/settings', 'account', data={})
            if not isinstance(data['account'], dict) or not data['account'].get('id'):
                raise SimklAPIError('invalid_response')
            self.store.set('profile', {'data': data, 'activity': activity})
            return data
