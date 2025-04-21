#!/usr/bin/env python3

# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import os
import platform
import re
import setuptools
import tarfile
import urllib.request

CREDENTIAL_PROVIDER_BASE = "https://github.com/Microsoft/artifacts-credprovider/releases/download/v1.4.0/"
CREDENTIAL_PROVIDER_NETFX = CREDENTIAL_PROVIDER_BASE + "Microsoft.NuGet.CredentialProvider.tar.gz"
CREDENTIAL_PROVIDER_NET8 = CREDENTIAL_PROVIDER_BASE + "Microsoft.Net8.NuGet.CredentialProvider.tar.gz"
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
    with urllib.request.urlopen(download_url) as fileobj:
        tar = tarfile.open(mode="r|gz", fileobj=fileobj)
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
        print(f"Unsupported OS: {os_system}. Please set the {CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME} environment variable to specify a runtime identifier.")
        return ""

    if os_arch.startswith('aarch64') or os_arch.startswith('arm64'):
        if (os_system == "windows"): # windows on ARM runs x64 binaries
            runtime_id += "-x64"
        else:
            runtime_id += "-arm64"
    if os_arch.startswith('x86_64') or os_arch.startswith('amd64'):
        runtime_id += "-x64"
    else:
        print(f"Unsupported architecture: {os_arch}. Please set the {CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME} environment variable to specify a runtime identifier.")
        return ""

    return runtime_id

def get_download_url():
    # Check if the environment variable is set for self-contained version
    # This can used for to override the auto-selected runtime identifier
    # for cases such as Docker builds.
    if CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME]:
            return CREDENTIAL_PROVIDER_NET8.replace(".Net8", f".Net8.{str(os.environ[CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME]).lower()}")
    
    use_net_8 = CREDENTIAL_PROVIDER_NET8_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_NET8_VAR_NAME] and \
        str(os.environ[CREDENTIAL_PROVIDER_NET8_VAR_NAME]).lower() == "true"

    use_non_sc = CREDENTIAL_PROVIDER_NON_SC_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_NON_SC_VAR_NAME] and \
        str(os.environ[CREDENTIAL_PROVIDER_NON_SC_VAR_NAME]).lower() == "true"

    if use_net_8 and use_non_sc:
        return CREDENTIAL_PROVIDER_NET8
    elif use_net_8:
        return CREDENTIAL_PROVIDER_NET8.replace(".Net8", f".Net8.{get_runtime_identifier()}")
    else:
        print(f"Selected .NET Framework 3.1 since {CREDENTIAL_PROVIDER_NET8_VAR_NAME} is not true and {CREDENTIAL_PROVIDER_SELF_CONTAINED_VAR_NAME} is not specified. Support for .NET 3.1 will be removed in the next major release version.")
        return CREDENTIAL_PROVIDER_NETFX

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    download_credential_provider(root)
    setuptools.setup(version=get_version(root))
