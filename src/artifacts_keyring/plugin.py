# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from __future__ import absolute_import

import json
import os
import requests
import subprocess
import sys

from . import __version__
from .support import Popen


class CredentialProvider(object):
    _NON_INTERACTIVE_VAR_NAME = "ARTIFACTS_KEYRING_NONINTERACTIVE_MODE"
    _CREDENTIALPROVIDER_PATH_VAR_NAME = "ARTIFACTS_KEYRING_CREDENTIALPROVIDER_PATH"
    _PLUGINS_ROOT = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "bin",
        "plugins",
        "netcore",
        "CredentialProvider.Microsoft"
    )

    def __init__(self):
        # All platforms: prefer ARTIFACTS_KEYRING_CREDENTIALPROVIDER_PATH if set
        custom_path = os.environ.get(self._CREDENTIALPROVIDER_PATH_VAR_NAME, "")

        if custom_path:
            tool_path = custom_path
        elif sys.platform.startswith("win"):
            tool_path = os.path.join(self._PLUGINS_ROOT, "CredentialProvider.Microsoft.exe")
        else:
            # non windows platforms do not use the .exe extension, and the binary may or may
            # not be self-contained (i.e. may require a .NET runtime to be installed)
            if os.path.exists(self._PLUGINS_ROOT):
                exe_path = os.path.join(self._PLUGINS_ROOT, 'CredentialProvider.Microsoft')
                try:
                    if os.path.exists(exe_path):
                        os.chmod(exe_path, 0o755)
                except Exception as e:
                    raise RuntimeError(
                        "Failed to set executable permissions for the Credential Provider at "
                        + self._PLUGINS_ROOT
                        + ". Error: " + str(e)
                    )

                # If the directory contains a runtimes folder, the binary is not
                # self-contained and requires a .NET install to run.
                if os.path.exists(os.path.join(self._PLUGINS_ROOT, "runtimes")):
                    tool_path = os.path.join(self._PLUGINS_ROOT, "CredentialProvider.Microsoft.dll")
                else:
                    tool_path = exe_path
            else:
                tool_path = os.path.join(self._PLUGINS_ROOT, "CredentialProvider.Microsoft")

        # Determine how to invoke the credential provider
        if tool_path.endswith(".dll"):
            self.exe = ["dotnet", "exec", tool_path]
        else:
            self.exe = [tool_path]

        if not os.path.isfile(tool_path):
            raise RuntimeError("Unable to find credential provider in the expected path: " + tool_path)

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


    def _is_upload_endpoint(self, url):
        url = url[: -1] if url[-1] == "/" else url
        return url.endswith("pypi/upload")


    def _can_authenticate(self, url, auth):
        response = requests.get(url, auth=auth)

        return response.status_code < 500 and \
            response.status_code != 401 and \
            response.status_code != 403


    def _get_credentials_from_credential_provider(self, url, is_retry):
        non_interactive = self._NON_INTERACTIVE_VAR_NAME in os.environ and \
            os.environ[self._NON_INTERACTIVE_VAR_NAME] and \
            str(os.environ[self._NON_INTERACTIVE_VAR_NAME]).lower() == "true"

        with Popen(
            self.exe + [
                "-Uri", url,
                "-IsRetry", str(is_retry),
                "-NonInteractive", str(non_interactive),
                "-CanShowDialog", "True",
                "-OutputFormat", "Json"
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        ) as proc:
            # Read all standard error first, which may either display
            # errors from the credential provider or instructions
            # from it for Device Flow authentication.
            for stderr_line in iter(proc.stderr.readline, b''):
                line = stderr_line.decode("utf-8", "ignore")
                sys.stderr.write(line)
                sys.stderr.flush()

            proc.wait()

            if proc.returncode != 0:
                stderr = proc.stderr.read().decode("utf-8", "ignore")

                error_msg = "Failed to get credentials: process with PID {pid} exited with code {code}".format(
                    pid=proc.pid, code=proc.returncode
                )
                if stderr.strip():
                    error_msg += "; additional error message: {error}".format(error=stderr)
                else:
                    error_msg += "; no additional error message available, see Credential Provider logs above for details."
                raise RuntimeError(error_msg)

            try:
                # stdout is expected to be UTF-8 encoded JSON, so decoding errors are not ignored here.
                payload = proc.stdout.read().decode("utf-8")
            except ValueError:
                raise RuntimeError("Failed to get credentials: the Credential Provider's output could not be decoded using UTF-8.")

            try:
                parsed = json.loads(payload)
                return parsed["Username"], parsed["Password"]
            except ValueError:
                raise RuntimeError("Failed to get credentials: the Credential Provider's output could not be parsed as JSON.")
