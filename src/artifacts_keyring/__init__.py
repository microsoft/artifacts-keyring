# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from __future__ import absolute_import

__author__ = "Microsoft Corporation <python@microsoft.com>"
__version__ = "1.0.0"

import warnings

from .support import urlsplit
from .plugin import CredentialProvider

import keyring.backend
import keyring.credentials


class ArtifactsKeyringBackend(keyring.backend.KeyringBackend):
    SUPPORTED_NETLOC = (
        "pkgs.dev.azure.com",
        "pkgs.visualstudio.com",
        "pkgs.codedev.ms",
        "pkgs.vsts.me",
    )
    _PROVIDER = CredentialProvider

    priority = 9.9

    def __init__(self):
        # In-memory cache of user-pass combination, to allow
        # fast handling of applications that insist on querying
        # username and password separately. get_password will
        # pop from this cache to avoid keeping the value
        # around for longer than necessary.
        self._cache = {}

    def get_credential(self, service, username):
        try:
            parsed = urlsplit(service)
        except Exception as exc:
            warnings.warn(str(exc))
            return None

        netloc = parsed.netloc.rpartition("@")[-1]

        if netloc is None or not netloc.endswith(self.SUPPORTED_NETLOC):
            return None

        cached = self._cache.setdefault(service, {})

        provider = self._PROVIDER()

        cred = provider.get_credentials(
            service,
            cached
            if username is None
            else {key: value for key, value in cached.items() if key == username},
        )

        if all(cred):
            _, password = cred

            if cred[0] == username:
                self._cache[service][username] = password
            else:
                username, _ = cred

            return keyring.credentials.SimpleCredential(username, password)

    def get_password(self, service, username):
        password = self._cache.get(service, {}).pop(username, None)
        if password is not None:
            return password

        # Fills the cache
        self.get_credential(service, username)

        # Empties the cache if username matches
        password = self._cache.get(service, {}).pop(username, None)
        if password is not None:
            return password

        return None

    def set_password(self, service, username, password):
        # Defer setting a password to the next backend
        raise NotImplementedError()

    def delete_password(self, service, username):
        # Try and remove it from the cache out of an abundance of caution
        self._cache.get(service, {}).pop(username, None)

        # Defer deleting a password to the next backend
        raise NotImplementedError()
