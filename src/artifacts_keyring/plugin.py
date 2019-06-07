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
