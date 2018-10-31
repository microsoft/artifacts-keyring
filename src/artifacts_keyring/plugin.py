from __future__ import absolute_import

import io
import json
import os
import subprocess
import sys
import uuid

from . import __version__
from .support import Popen


class CredentialProvider(object):
    def __init__(self):
        if sys.platform.startswith("win"):
            self.exe = [
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
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
                    "netcore",
                    "CredentialProvider.Microsoft",
                    "CredentialProvider.Microsoft.dll",
                ),
            ]

        self.proc = p = Popen(
            self.exe + ["-P"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        inputs = io.TextIOWrapper(p.stdout, "utf-8", "replace")
        self._in = (json.loads(d) for d in inputs)
        self._messages = {}

    def _kill(self):
        p, self.proc = self.proc, None
        if p:
            try:
                p.kill()
            except OSError:
                pass

    def _read1(self, method):
        pending = self._messages.get(method)
        if pending:
            return pending.pop(0)
        for msg in self._in:
            if msg["Type"] == "Progress":
                self.send(**msg)
                continue
            if msg["Method"] == method:
                return msg
            self._messages.setdefault(msg["Method"], []).append(msg)

    def _read(self, method):
        msg = self._read1(method)
        if msg and msg["Type"] == "Fault":
            raise RuntimeError(msg["Payload"].get("Message", msg))
        return msg

    def __enter__(self):
        if not self.proc:
            raise RuntimeError("process already terminated")

        if not self.handshake():
            self._kill()
            raise RuntimeError("failed to complete handshake")

        if not self.initialize():
            self._kill()
            raise RuntimeError("failed to initialize")

        return self

    def __exit__(self, ex_type, ex_value, ex_tb):
        self.send(Method="Close", Type="Request")

    def send(self, **kwargs):
        kwargs.setdefault("RequestId", str(uuid.uuid4()))
        data = (json.dumps(kwargs) + "\r\n").encode("utf-8", "strict")
        p = self.proc
        if p:
            p.stdin.write(data)
            p.stdin.flush()

    def reply(self, req, **kwargs):
        return self.send(
            RequestId=req["RequestId"],
            Method=req["Method"],
            Type="Response",
            Payload=kwargs,
        )

    def handshake(self):
        while True:
            req = self._read("Handshake")
            if not req:
                return

            if req["Type"] == "Request":
                protocol = req["Payload"]["MinimumProtocolVersion"]
                if protocol.startswith(("1.", "2.")):
                    self.reply(req, ResponseCode="Success", ProtocolVersion="2.0.0")
                    return True
                else:
                    self.reply(ResponseCode="Error")

                raise RuntimeError("Cannot negotiate protocol")

            if req["Type"] == "Response":
                if req["Payload"]["ResponseCode"] == "Success":
                    return True

                raise RuntimeError(req["Payload"])

            raise RuntimeError(req)

    def initialize(self):
        self.send(
            Type="Request",
            Method="Initialize",
            Payload=dict(
                clientVersion=__version__, culture="en-US", requestTimeout="00:00:05.00"
            ),
        )

        while True:
            req = self._read("Initialize")
            if req is None:
                raise RuntimeError("failed to initialize")

            if req["Type"] == "Response":
                if req["Payload"]["ResponseCode"] == "Success":
                    return True

                raise RuntimeError(req["Payload"])

            raise RuntimeError(req)

    def get_credentials(self, url, allow_prompt=False):
        self.send(
            Type="Request",
            Method="GetAuthenticationCredentials",
            Payload=dict(
                uri=url,
                IsRetry=False,
                IsNonInteractive=not allow_prompt,
                CanShowDialog=allow_prompt,
            ),
        )

        while True:
            req = self._read("GetAuthenticationCredentials")
            if not req:
                raise RuntimeError("failed to get credentials")
            elif req["Type"] == "Response":
                payload = req["Payload"]
                if payload["ResponseCode"] == "Success":
                    return payload["Username"], payload["Password"]
                elif payload["ResponseCode"] == "NotFound":
                    return None, None
                else:
                    raise RuntimeError(payload["ResponseCode"])
            else:
                break
