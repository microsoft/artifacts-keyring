## NOTE
'artifacts-keyring' is a relatively thin wrapper around [artifacts-credprovider](https://github.com/microsoft/artifacts-credprovider).  Make sure to also look at that repository for more information about different scenarios. For example:

* [Environment variable to explicitly override tokens](https://github.com/microsoft/artifacts-credprovider)
* [Safely using credentials in docker](https://github.com/dotnet/dotnet-docker/blob/master/documentation/scenarios/nuget-credentials.md#using-the-azure-artifact-credential-provider)

# artifacts-keyring

The `artifacts-keyring` package provides authentication for publishing or consuming Python packages to or from Azure Artifacts feeds within [Azure DevOps](https://azure.com/devops).

This package is an extension to [keyring](https://pypi.org/project/keyring), which will automatically find and use it once installed.

Both [pip](https://pypi.org/project/pip) and [twine](https://pypi.org/project/twine) will use `keyring` to
find credentials.

## Installation

As of version 23.1 Pip can use the `keyring` as a command line application in addition to importing it as a python library.
This allows one to install keyring such that it can be found on the PATH.
Go to [Pip's Authentication documentation](https://pip.pypa.io/en/stable/topics/authentication/#) for up-to-date information on all Pip's authentication abilities.

The CLI is a one time installation, assuming one of the following is true:
- The `virtualenv` cli/library is (indirectly) used to create new virtual environments.
- You only use Python versions new enough that the following returns 23.1 or higher.
  ```
  python -m venv .venv
  .venv/Scripts/pip.exe --version
  ```

### Common
If you don't want to/can supply the private index url for each command there are two alternatives:
- run `pip config set global.index-url <your URL here>`. To configure once for all users add the `--global` flag.
- Set environment variable `PIP_INDEX_URL` to you url.

The same applies to extra index urls. `PIP_EXTRA_INDEX_URL` is the name of the environment variable and `global.extra-index-url` is the value to provide `pip config set`.

### Install via pipx as a CLI
```powershell
#powershell
python -m venv temp
. ./Scripts/activate.ps1
$global = Read-Host "To install for current user only, press enter. To install for all users, which requires admin permissions, type '--global' (no quotes)"
pip config set global.keyring-provider subprocess $global
pip install pipx --index https://pypi.org/simple/
pipx install pipx
pipx ensurepath
rmdir temp
exit
```

To install this package, for every new python environment, run the following `pip` command:

```
pip install artifacts-keyring --index https://pypi.org/simple/
```

## Usage

When using keyring via the CLI (provider `subprocess`) you MUST use `VssSessionToken` as the username component in the url.
For the `import` provider that should not be required, unless a very old version of the `keyring` package is installed. 

### Requirements

To use `artifacts-keyring` to set up authentication between `pip`/`twine` and Azure Artifacts, the following requirements must be met:

* pip version **19.2** or higher
* twine version **1.13.0** or higher
* python version **3.0** or higher
* .Net SDK is installed. Refer to [here](https://docs.microsoft.com/en-us/dotnet/core/install/linux-ubuntu) for installation guideline.

### Publishing packages to an Azure Artifacts feed
Once `artifacts-keyring` is installed, to publish a package, use the following `twine` command, replacing **<org_name>** and **<feed_name>** with your own:

```
twine upload --repository-url https://pkgs.dev.azure.com/<org_name>/_packaging/<feed_name>/pypi/upload <package_wheel_or_other_dist_format>
```

### Installing packages from an Azure Artifacts feed
Once `artifacts-keyring` is installed, to consume a package, use the following `pip` command, replacing **<org_name>** and **<feed_name>** with your own, and **<package_name>** with the package you want to install:

```
pip install <package_name> --index-url https://pkgs.dev.azure.com/<org_name>/_packaging/<feed_name>/pypi/simple
```

## Advanced configuration
The `artifacts-keyring` package is layered on top of our [Azure Artifacts Credential Provider](https://github.com/microsoft/artifacts-credprovider). Check out that link to the GitHub repo for more information on configuration options.

### Environment variables

- `ARTIFACTS_KEYRING_NONINTERACTIVE_MODE`: Controls whether the underlying credential provider can issue interactive prompts.

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
