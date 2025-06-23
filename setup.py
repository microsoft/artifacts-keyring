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
import tarfile
import urllib.request
import shutil
from setuptools import Distribution, setup
from setuptools.command.build_py import build_py
from setuptools.command.bdist_wheel import bdist_wheel

CREDENTIAL_PROVIDER_BASE = "https://github.com/Microsoft/artifacts-credprovider/releases/download/v1.4.1/"
CREDENTIAL_PROVIDER_NET8 = CREDENTIAL_PROVIDER_BASE + "Microsoft.Net8.NuGet.CredentialProvider.tar.gz"
CREDENTIAL_PROVIDER_NET8_ZIP = CREDENTIAL_PROVIDER_BASE + "Microsoft.Net8.NuGet.CredentialProvider.zip"
CREDENTIAL_PROVIDER_NON_SC_VAR_NAME = "ARTIFACTS_CREDENTIAL_PROVIDER_NON_SC"
CREDENTIAL_PROVIDER_RID_VAR_NAME = "ARTIFACTS_CREDENTIAL_PROVIDER_RID"

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
        print(f"Warning: Unsupported OS: {os_system}. Please set the {CREDENTIAL_PROVIDER_RID_VAR_NAME} environment variable to specify a runtime identifier.")
        return ""

    if "aarch64" in os_arch or "arm64" in os_arch:
        if (os_system == "windows"): # windows on ARM runs x64 binaries
            runtime_id += "-x64"
        else:
            runtime_id += "-arm64"
    elif "x86_64" in os_arch or "amd64" in os_arch:
        runtime_id += "-x64"
    else:
        print(f"Warning: Unsupported architecture: {os_arch}. Please set the {CREDENTIAL_PROVIDER_RID_VAR_NAME} environment variable to specify a runtime identifier.")
        return ""

    return runtime_id

def get_os_runtime_url(runtime_var):
    if runtime_var == "" and "osx" in runtime_var:
        return CREDENTIAL_PROVIDER_NET8_ZIP
    elif runtime_var == "":
        return CREDENTIAL_PROVIDER_NET8

    if "osx" in runtime_var:
        return CREDENTIAL_PROVIDER_NET8_ZIP.replace(".Net8", f".Net8.{runtime_var}")

    return CREDENTIAL_PROVIDER_NET8.replace(".Net8", f".Net8.{runtime_var}")

def get_download_url():
    # When building the platform wheels in CI, use the self-contained version of the credential provider.
    # In these cases, check ARTIFACTS_CREDENTIAL_PROVIDER_RID to determine the desired runtime identifier.
    if CREDENTIAL_PROVIDER_RID_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_RID_VAR_NAME]:
            runtime_var = str(os.environ[CREDENTIAL_PROVIDER_RID_VAR_NAME]).lower()
            return get_os_runtime_url(runtime_var)
    
    # Specify whether they want self-contained auto-detection or not.
    # Only applicable for non-CI environments.
    use_non_sc = CREDENTIAL_PROVIDER_NON_SC_VAR_NAME in os.environ and \
        os.environ[CREDENTIAL_PROVIDER_NON_SC_VAR_NAME] and \
        str(os.environ[CREDENTIAL_PROVIDER_NON_SC_VAR_NAME]).lower() == "true"

    if use_non_sc:
        return CREDENTIAL_PROVIDER_NET8
    else:
        runtime_id = str(get_runtime_identifier())
        return get_os_runtime_url(runtime_id)


def download_credential_provider(dest):
    if not os.path.isdir(dest):
        os.makedirs(dest)

    print("Downloading and extracting artifacts-credprovider to", dest)
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
                tar.extractall(dest, filter="data")
            else:
                tar.extractall(dest)

class BuildKeyring(build_py):
    def run(self):
        super().run()

class BuildKeyringPlatformWheel(bdist_wheel):
    def finalize_options(self):
        super().finalize_options()
        self.root_is_pure = False

class KeyringDistribution(Distribution):
    def has_ext_modules(self):
        return True

if __name__ == "__main__":
    root = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(root, "src", "artifacts_keyring", "plugins")

    # Clean any previous build artifacts
    if os.path.exists(dest):
        print("Removing previous plugins artifacts in ", dest)
        shutil.rmtree(dest)

    download_credential_provider(dest)

	# Fix for liblttng-ust.so.0 not being found on Debian 12 and later.
    # See https://github.com/dotnet/runtime/issues/57784 for more info.
    clr_trace_path = os.path.join(
        dest,
        "plugins",
        "netcore",
        "CredentialProvider.Microsoft",
        "libcoreclrtraceptprovider.so",
    )
    if os.path.exists(clr_trace_path):
        print("Removing libcoreclrtraceptprovider.so from plugins directory")
        os.remove(clr_trace_path)
    
    setup(
        version=get_version(root),
        cmdclass={
            "build_py": BuildKeyring,
            "bdist_wheel": BuildKeyringPlatformWheel,
        },
        distclass=KeyringDistribution,
    )
