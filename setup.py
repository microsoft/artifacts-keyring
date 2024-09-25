#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
import re
import setuptools
import shutil
import sys
import tarfile
import tempfile
import urllib.request

CREDENTIAL_PROVIDER = (
    "https://github.com/Microsoft/artifacts-credprovider/releases/download/"
    + "v1.2.3"
    + "/Microsoft.NuGet.CredentialProvider.tar.gz"
    )


def download_credential_provider(root):
    dest = os.path.join(root, "src", "artifacts_keyring", "plugins")

    if not os.path.isdir(dest):
        os.makedirs(dest)

    print("Downloading and extracting to", dest)
    with urllib.request.urlopen(CREDENTIAL_PROVIDER) as fileobj:
        tar = tarfile.open(mode="r|gz", fileobj=fileobj)
        tar.extractall(dest)


def get_version(root):
    src = os.path.join(root, "src", "artifacts_keyring", "__init__.py")

    with open(src, "r", encoding="utf-8", errors="strict") as f:
        txt = f.read()

    m = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", txt)
    return m.group(1) if m else "0.1.0"


if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    download_credential_provider(root)
    setuptools.setup(version=get_version(root))
