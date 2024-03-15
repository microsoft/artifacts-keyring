# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

"""Helper imports for the Azure DevOps Keyring module.
"""

# *********************************************************
# Import the correct urlsplit function

try:
    from urllib.parse import urlsplit
except ImportError:
    from urlparse import urlsplit


# *********************************************************
# Import (and possibly update) subprocess.Popen

from subprocess import Popen

if not hasattr(Popen, "__enter__"):
    # Handle Python 2.x not making Popen a context manager
    class Popen(Popen):
        def __enter__(self):
            return self

        def __exit__(self, ex_type, ex_value, ex_tb):
            pass

# *********************************************************
# Patch DefaultAzureCredential to have DeviceCodeCredential

import logging
from azure.identity import (
    DeviceCodeCredential,
    DefaultAzureCredential,
    ChainedTokenCredential
)
_LOGGER = logging.getLogger(__name__)
class DefaultAzureCredentialWithDevicecode(ChainedTokenCredential):
    def __init__(self, *args, **kwargs):
        # extract devicecode kwargs & instantiate DevicecodeCredential
        devicecode_kwargs = dict(kwargs)
        tenant_id = kwargs.pop('tenant_id', None)
        client_id = kwargs.pop('devicecode_client_id', None)
        if tenant_id:
            devicecode_kwargs['tenant_id'] = tenant_id
        if client_id:
            devicecode_kwargs['client_id'] = client_id
        devicecode_credential = DeviceCodeCredential(**devicecode_kwargs)
        
        # instantiate DefaultAzureCredential and get a list of the default credentials
        credentials = DefaultAzureCredential(*args, **kwargs).credentials
        credentials = list(credentials)
        
        # append the devicecode credential to the list of defaults        
        credentials.append(devicecode_credential)

        # instantiate self as a ChainedTokenCredential with the devicecode credential added
        super().__init__(*credentials)

    def get_token(self, *scopes, **kwargs):
        # type: (*str, **Any) -> AccessToken
        """Request an access token for `scopes`.

        This method is called automatically by Azure SDK clients.

        :param str scopes: desired scopes for the access token. This method requires at least one scope.
        :keyword str tenant_id: optional tenant to include in the token request.

        :rtype: :class:`azure.core.credentials.AccessToken`

        :raises ~azure.core.exceptions.ClientAuthenticationError: authentication failed. The exception has a
          `message` attribute listing each authentication attempt and its error message.
        """
        if self._successful_credential:
            token = self._successful_credential.get_token(*scopes, **kwargs)
            _LOGGER.info(
                "%s acquired a token from %s", self.__class__.__name__, self._successful_credential.__class__.__name__
            )
            return token

        return super().get_token(*scopes, **kwargs)