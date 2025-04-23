#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import io
import os
import platform
import re
import sys
import zipfile
import setuptools
import tarfile
import urllib.request

CREDENTIAL_PROVIDER_BASE = "https://github.com/Microsoft/artifacts-credprovider/releases/download/v1.4.1/"
CREDENTIAL_PROVIDER_NETFX = CREDENTIAL_PROVIDER_BASE + "Microsoft.NuGet.CredentialProvider.tar.gz"
CREDENTIAL_PROVIDER_NET8 = CREDENTIAL_PROVIDER_BASE + "Microsoft.Net8.NuGet.CredentialProvider.tar.gz"
CREDENTIAL_PROVIDER_NET8_ZIP = CREDENTIAL_PROVIDER_BASE + "Microsoft.Net8.NuGet.CredentialProvider.zip"
CREDENTIAL_PROVIDER_NET8_VAR_NAME = "ARTIFACTS_KEYRING_USE_NET8"
CREDENTIAL_PROVIDER_NON_SC_VAR_NAME = "ARTIFACTS_KEYRING_NON_SELF_CONTAINED"
CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME = "ARTIFACTS_CREDENTIAL_PROVIDER_RID"

def download_credential_provider(root):
    dest = os.path.join(root, "src", "artifacts_keyring", "plugins")

    if not os.path.isdir(dest):
        os.makedirs(dest)

    print("Downloading and extracting to", dest)
    download_url = get_download_url()
    print("Downloading artifacts-credprovider from", download_url)

    with urllib.request.urlopen(download_url) as download_file:
        if download_url.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(download_file.read())) as zip_file:
                zip_file.extractall(dest)
        else:
            tar = tarfile.open(mode="r|gz", fileobj=download_file)

            # Python 3.12 adds a safety filter for tar extraction
            # to prevent placement of files outside the target directory.
            # https://docs.python.org/3.12/library/tarfile.html#tarfile.tar_filter
            if sys.version_info >= (3, 12):
                tar.extractall(dest, filter='data')
            else:
                tar.extractall(dest)

def get_version(root):
    src = os.path.join(root, "src", "artifacts_keyring", "__init__.py")

    with open(src, "r", encoding="utf-8", errors="strict") as f:
        txt = f.read()

    m = re.search(r"__version__\s*=\s*['\"](.+?)['\"]", txt)
    return m.group(1) if m else "0.1.0"

def get_runtime_identifier():
    os_system = platform.system().lower()
    os_arch = platform.machine().lower()
    
    if os_system == "linux":
        runtime_id = "linux"
    elif os_system == "darwin":
        runtime_id = "osx"
    elif os_system == "windows":
        runtime_id = "win"
    else:
        print(f"Warning: Unsupported OS: {os_system}. Please set the {CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME} environment variable to specify a runtime identifier.")
        return ""

    if os_arch.startswith('aarch64') or os_arch.startswith('arm64'):
        if (os_system == "windows"): # windows on ARM runs x64 binaries
            runtime_id += "-x64"
        else:
            runtime_id += "-arm64"
    if os_arch.startswith('x86_64') or os_arch.startswith('amd64'):
        runtime_id += "-x64"
    else:
        print(f"Warning: Unsupported architecture: {os_arch}. Please set the {CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME} environment variable to specify a runtime identifier.")
        return ""

    return runtime_id

def get_download_url():
    # Check if the environment variable is set for self-contained version
    # This can used for to override the auto-selected runtime identifier
    # for cases such as Docker builds.
    if CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME]:
            runtime_var = str(os.environ[CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME]).lower()
            if runtime_var.startswith("osx"):
                return CREDENTIAL_PROVIDER_NET8_ZIP.replace(".Net8", f".Net8.{runtime_var}")

            return CREDENTIAL_PROVIDER_NET8.replace(".Net8", f".Net8.{runtime_var}")
    
    use_net_8 = CREDENTIAL_PROVIDER_NET8_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_NET8_VAR_NAME] and \
        str(os.environ[CREDENTIAL_PROVIDER_NET8_VAR_NAME]).lower() == "true"

    use_non_sc = CREDENTIAL_PROVIDER_NON_SC_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_NON_SC_VAR_NAME] and \
        str(os.environ[CREDENTIAL_PROVIDER_NON_SC_VAR_NAME]).lower() == "true"

    if use_net_8 and use_non_sc:
        return CREDENTIAL_PROVIDER_NET8
    elif use_net_8:
        runtime_id = str(get_runtime_identifier())
        if runtime_id.startswith("osx"):
            # macOS does not publish .tar.gz files, use the .zip version instead
            return CREDENTIAL_PROVIDER_NET8_ZIP.replace(".Net8", f".Net8.{runtime_id}")

        return CREDENTIAL_PROVIDER_NET8.replace(".Net8", f".Net8.{runtime_id}")
    else:
        print(f"Warning: Selected .NET Framework 4.6.1 since {CREDENTIAL_PROVIDER_NET8_VAR_NAME} is not true and {CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME} is not specified. Support for .NET Framework 4.6.1 will be removed in the next major release version.")
        return CREDENTIAL_PROVIDER_NETFX

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    download_credential_provider(root)
    setuptools.setup(version=get_version(root))
