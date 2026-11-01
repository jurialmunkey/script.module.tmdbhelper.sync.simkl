class SimklAPIError(Exception):
    def __init__(self, code, status=0, message=None):
        self.code = code
        self.status = status
        super().__init__(message or f'SIMKL: {code} (HTTP {status})')
