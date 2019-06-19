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
    def __init__(self):
        if sys.platform.startswith("win"):
            self.exe = [
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "plugins",
                    "plugins",
                    "netfx",
                    "CredentialProvider.Microsoft",
                    "CredentialProvider.Microsoft.exe",
                )
            ]
        else:
            try:
                from dotnetcore2.runtime import get_runtime_path
            except ImportError:
                get_runtime_path = lambda: "dotnet"
            self.exe = [
                get_runtime_path(),
                "exec",
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "plugins",
                    "plugins",
                    "netcore",
                    "CredentialProvider.Microsoft",
                    "CredentialProvider.Microsoft.dll",
                ),
            ]


    def get_credentials(self, url):
        # Getting credentials with IsRetry=false; the credentials may come from the cache
        username, password = self._get_credentials_from_credential_provider(url, is_retry=False)

        # Do not attempt to validate if the credentials could not be obtained
        if username is None or password is None:
            return username, password

        # Make sure the credentials are still valid (i.e. not expired)
        if self._are_credentials_valid(url, username, password):
            return username, password

        # The cached credentials are expired; get fresh ones with IsRetry=true
        return self._get_credentials_from_credential_provider(url, is_retry=True)


    def _are_credentials_valid(self, url, username, password):
        response = requests.get(url, auth=(username, password))

        return response.status_code < 500 and \
            response.status_code != 401 and \
            response.status_code != 403


    def _get_credentials_from_credential_provider(self, url, is_retry):
        proc = Popen(
            self.exe + [
                "-Uri", url,
                "-IsRetry", str(is_retry),
                "-NonInteractive", "False",
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
            sys.stdout.write(line)
            sys.stdout.flush()

        proc.wait()

        if proc.returncode != 0:
            stderr = proc.stderr.read().decode("utf-8", "ignore")
            raise RuntimeError("Failed to get credentials: process with PID {pid} exited with code {code}; error: {error}"
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

