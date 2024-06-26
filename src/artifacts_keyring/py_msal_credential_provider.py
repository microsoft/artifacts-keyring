import json, sys, os, datetime as dt

import logging
import requests
from .support import DefaultAzureCredentialWithDevicecode
from azure.core.exceptions import ClientAuthenticationError
from azure.identity import DeviceCodeCredential


# logging.getLogger("azure.identity._credentials.chained").setLevel(logging.ERROR)
logging.getLogger("azure.identity._credentials.managed_identity").setLevel(logging.ERROR)
logging.getLogger("azure.identity._credentials.environment").setLevel(logging.ERROR)
logging.getLogger("azure.identity._credentials.vscode").setLevel(logging.ERROR)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.ERROR)

class PyMSALCredentialProvider:
    def __init__(self):
        # these values are from https://github.com/microsoft/artifacts-credprovider/blob/cdc427e8236212b33041b4276961855b39bbe98d/CredentialProvider.Microsoft/CredentialProviders/Vsts/MSAL/MsalTokenProviderFactory.cs#L12
        self._oauth_client_id = '872cd9fa-d31f-45e0-9eab-6e460a02d1f1'
        self._oauth_scope = '499b84ac-1321-427f-aa17-267ca6975798/.default'
        self._oauth_authority = None
        self._vsts_authority = None

        # read/write PAT scope bu default
        self._vsts_scope = os.getenv('MSAL_ADO_PAT_SCOPE', 'vso.packaging_write')
        self._pat_duration = int(os.getenv('MSAL_ADO_PAT_DURATION', '90')) # days
        self._default_username = os.getenv('MSAL_ADO_USERNAME', 'VssSessionToken')
        
        self._exclude_shared_token_cache = os.getenv(
            'MSAL_EXCLUDE_SHARED_TOKEN_CACHE', 'False') == 'True'

    def get_credentials(self, url):
        # Public feed short circuit: return nothing if not getting credentials for the upload endpoint
        # (which always requires auth) and the endpoint is public (can authenticate without credentials).
        if not self._is_upload_endpoint(url) and self._can_authenticate(url, None):
            return None, None

        # Getting credentials with IsRetry=false; the credentials may come from the cache
        username, password = self._get_credentials_from_credential_provider(url, is_retry=False)

        # Do not attempt to validate if the credentials could not be obtained
        if username is None or password is None:
            return username, password

        # Make sure the credentials are still valid (i.e. not expired)
        if self._can_authenticate(url, (username, password)):
            return username, password

        # The cached credentials are expired; get fresh ones with IsRetry=true
        return self._get_credentials_from_credential_provider(url, is_retry=True)

    def _get_credentials_from_credential_provider(self, url, is_retry):
        self._oauth_authority, self._vsts_authority =  self._get_authorities(url)

        bearer_token = self._get_bearer_token()
        pat = self._exchange_bearer_for_pat(bearer_token)

        username = self._default_username
        password = pat
        return username, password

    def _get_authorities(self, url):
        """ send a GET to the url and parse the response header """
        # send GET request
        response = requests.get(url)
        headers = response.headers

        # extract oauth authority
        bearer_authority = headers['WWW-Authenticate']
        bearer_authority = bearer_authority.split(',')[0]
        bearer_authority = bearer_authority.replace(
            'Bearer authorization_uri=', '')

        # extract Visual Studo authority
        pat_authority = headers['X-VSS-AuthorizationEndpoint']
        return bearer_authority, pat_authority

    def _get_pat_expiry(self, start=None):
        if not start:
            start = dt.datetime.now(dt.timezone.utc)
        expiry = start + dt.timedelta(days=self._pat_duration)
        expiry = expiry.strftime('%Y-%m-%dT%H:%M:%SZ')
        return expiry

    def _get_bearer_token(self):
        """ Tries to get bearer token using 
        1. EnvironmentCredential (deployed service)
        2. ManagedIdentityCredential (deployed service)
        3. AzureCliCredential (signed-in developer)
        4. AzurePowerShellCredential (signed-in developer)
        5. SharedTokenCacheCredential (cached from other applications)
        6. DeviceCodeCredential (interactive developer)
        """
        authority, _, tenant_id = self._oauth_authority.rpartition('/')
        try:
            token = DefaultAzureCredentialWithDevicecode(
                managed_identity_client_id=self._oauth_client_id,
                authority=authority,
                exclude_shared_token_cache_credential=self._exclude_shared_token_cache,
                devicecode_client_id=self._oauth_client_id,
                tenant_id=tenant_id,
            ).get_token(self._oauth_scope).token
        except ClientAuthenticationError as e:
            if 'Azure Active Directory error' not in str(e):
                raise e
            # msg = (f"Caught {e.__class__}: {str(e)}. This is most likely due to a "
            #         "an expired token in the shared token cache. To mitigate, you can:"
            #         "1) retry the same command, or 2) sign in with az cli, or"
            #         "3) retry the same command with the environment variable "
            #         "`MSAL_EXCLUDE_SHARED_TOKEN_CACHE=True` set.")
            # raise ClientAuthenticationError(msg)
            """ 
            DefaultAzureCredential raises an exception when there is a token
            found in the cache but the token has expired. This issue has
            been raised https://github.com/Azure/azure-sdk-for-python/issues/21718#issuecomment-974225195 
            and it is a design choice of the azure-identity developers. However,
            for our use case, the fallback below requires user intervention and therefore
            the concerns about accidentally operating on the incorrect account are not 
            applicable. Hence we explicitly catch the error and initiate the 
            DeviceCode flow. This behaviour is the same as re-running the command 
            with `MSAL_EXCLUDE_SHARED_TOKEN_CACHE=True`, which has the same effect as 
            the suggestion linked in the GH issue above.
            """
            print(f"Caught {e.__class__}: {str(e)}! Falling back to devicecode flow")
            token = DeviceCodeCredential(
                authority=authority,
                tenant_id=tenant_id,
                client_id=self._oauth_client_id
            ).get_token(self._oauth_scope).token
        return token

    def _exchange_bearer_for_pat(self, bearer_token):
        # NOTE: uses the new version of the api, different from the one used in artifacts-credprovider

        # build request headers
        request_headers = {
            'Authorization': f"Bearer {bearer_token}",
            'Content-Type': "application/json",
            'User-Agent':'PyMSALCredentialProvider'
        }

        # build the request url
        base_endpoint = self._vsts_authority.rstrip('/')
        token_api_route = '/_apis/tokens/pats?api-version=7.1-preview.1'
        visual_studio_url = base_endpoint + token_api_route
        
        # build the request payload
        expiry = self._get_pat_expiry()
        request_payload = {
            'displayName': 'Azure DevOps Artifacts PyMSAL Credential Provider',
            'scope':self._vsts_scope,
            'validTo': expiry,
            'allOrgs':'false'
        }

        # send request
        response = requests.post(
            visual_studio_url,
            headers=request_headers,
            json=request_payload)

        response = response.json()
        pat = response['patToken']['token']
        return pat

    def _is_upload_endpoint(self, url):
        url = url[: -1] if url[-1] == "/" else url
        return url.endswith("pypi/upload")


    def _can_authenticate(self, url, auth):
        response = requests.get(url, auth=auth)

        return response.status_code < 500 and \
            response.status_code != 401 and \
            response.status_code != 403
