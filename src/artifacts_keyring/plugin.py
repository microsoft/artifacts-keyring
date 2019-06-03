# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from __future__ import absolute_import

import json
import os
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
    
    def get_credentials(self, url, allow_prompt=False):
        proc = Popen(
            self.exe + [
                "-Uri", url,
                "-IsRetry", "False",
                "-NonInteractive", str(not allow_prompt),
                "-CanShowDialog", str(allow_prompt),
                "-OutputFormat", "Json"
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        outs = errs = None

        if sys.version_info >= (3, 3):
            try:
                outs, errs = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired as e:
                proc.kill()
                outs, errs = proc.communicate()
                raise e
        else:
            # Timeout was introduced in Python 3.3
            outs, errs = proc.communicate()

        if errs:
            raise RuntimeError("Failed to get credentials: " + errs.decode("utf-8", "ignore"))

        try:
            payload = outs.decode("utf-8")
        except ValueError:
            raise RuntimeError("Failed to get credentials: the Credential Provider's output could not be decoded using UTF-8.")

        try:
            parsed = json.loads(payload)
            return parsed["Username"], parsed["Password"]
        except ValueError:
            raise RuntimeError("Failed to get credentials: the Credential Provider's output could not be parsed as JSON.")
