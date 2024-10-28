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

CREDENTIAL_PROVIDER_BASE = "https://github.com/Microsoft/artifacts-credprovider/releases/download/v1.3.0/"
CREDENTIAL_PROVIDER_NETFX = CREDENTIAL_PROVIDER_BASE + "Microsoft.NuGet.CredentialProvider.tar.gz"
CREDENTIAL_PROVIDER_NET8 = CREDENTIAL_PROVIDER_BASE + "Microsoft.Net8.NuGet.CredentialProvider.tar.gz"
CREDENTIAL_PROVIDER_NET_VER_VAR_NAME = "ARTIFACTS_KEYRING_USE_NET8"

def download_credential_provider(root):
    dest = os.path.join(root, "src", "artifacts_keyring", "plugins")

    if not os.path.isdir(dest):
        os.makedirs(dest)

    print("Downloading and extracting to", dest)
    download_url = get_download_url()
    print("Downloading artifacts-credprovider from", download_url)
    with urllib.request.urlopen(download_url) as fileobj:
        tar = tarfile.open(mode="r|gz", fileobj=fileobj)
        tar.extractall(dest)

def get_version(root):
    src = os.path.join(root, "src", "artifacts_keyring", "__init__.py")

    with open(src, "r", encoding="utf-8", errors="strict") as f:
        txt = f.read()

    m = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", txt)
    return m.group(1) if m else "0.1.0"

def get_download_url():
    use_net_8 = CREDENTIAL_PROVIDER_NET_VER_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_NET_VER_VAR_NAME] and \
        str(os.environ[CREDENTIAL_PROVIDER_NET_VER_VAR_NAME]).lower() == "true"

    return CREDENTIAL_PROVIDER_NET8 if use_net_8 else CREDENTIAL_PROVIDER_NETFX

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    download_credential_provider(root)
    setuptools.setup(version=get_version(root))
