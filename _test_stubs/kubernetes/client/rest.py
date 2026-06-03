"""Minimal stub for kubernetes.client.rest used in local test runs."""


class ApiException(Exception):
    def __init__(self, status=None, reason=None, **kwargs):
        self.status = status
        self.reason = reason
        super().__init__(reason)
