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
import warnings
import shutil

from . import __version__
from .support import Popen


class CredentialProvider(object):
    _NON_INTERACTIVE_VAR_NAME = "ARTIFACTS_KEYRING_NONINTERACTIVE_MODE"

    def __init__(self):
        if sys.platform.startswith("win"):
            tool_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "plugins",
                "plugins",
                "netfx",
                "CredentialProvider.Microsoft",
                "CredentialProvider.Microsoft.exe",
            )
            self.exe = [tool_path]
        else:
            try:
                # check to see if any dotnet runtimes are installed. Not checking specific versions.
                output = subprocess.check_output(["dotnet", "--list-runtimes"]).decode().strip()
                if(len(output) == 0):
                    raise Exception("No dotnet runtime found. Refer to https://learn.microsoft.com/dotnet/core/install/ for installation guidelines.")
            except Exception as e:
                message = (
                    "Unable to find dependency dotnet, please manually install"
                    " the .NET runtime and ensure 'dotnet' is in your PATH. Error: "
                )
                raise Exception(message + str(e))

            tool_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "plugins",
                "plugins",
                "netcore",
                "CredentialProvider.Microsoft",
                "CredentialProvider.Microsoft.dll",
            )
            self.exe = ["dotnet", "exec", tool_path]

        if not os.path.exists(tool_path):
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

        proc = Popen(
            self.exe + [
                "-Uri", url,
                "-IsRetry", str(is_retry),
                "-NonInteractive", str(non_interactive),
                "-CanShowDialog", "False",
                "-OutputFormat", "Json"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

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
            raise RuntimeError("Failed to get credentials: process with PID {pid} exited with code {code}; additional error message: {error}"
                .format(pid=proc.pid, code=proc.returncode, error=stderr))

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
