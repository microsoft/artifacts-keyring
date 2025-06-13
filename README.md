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

To install this package, run the following `pip` command:

```
pip install artifacts-keyring
```

## Usage

### Requirements

To use `artifacts-keyring` to set up authentication between `pip`/`twine` and Azure 
Artifacts, the following requirements must be met:

* pip version **19.2** or higher
* twine version **1.13.0** or higher
* python version **3.9** or higher

  ```
  If no matching platform specific .whl is found when running pip install and the sdist is 
  fetched instead, the .NET runtime 8.0.X or later is required. Refer to [here](https://
  learn.microsoft.com/dotnet/core/install/) for installation guideline.
  ```

### Publishing packages to an Azure Artifacts feed
Once `artifacts-keyring` is installed, to publish a package, use the following `twine` 
command, replacing **<org_name>** and **<feed_name>** with your own:

```
twine upload --repository-url https://pkgs.dev.azure.com/<org_name>/_packaging/<feed_name>/pypi/upload <package_wheel_or_other_dist_format>
```

### Installing packages from an Azure Artifacts feed
Once `artifacts-keyring` is installed, to consume a package, use the following `pip` command, replacing 
**<org_name>** and **<feed_name>** with your own, and **<package_name>** with the package you want to install:

```
pip install <package_name> --index-url https://pkgs.dev.azure.com/<org_name>/_packaging/<feed_name>/pypi/simple
```

## Advanced configuration
The `artifacts-keyring` package is layered on top of our [Azure Artifacts Credential Provider](https://github.com/microsoft/artifacts-credprovider). 
Check out that link to the GitHub repo for more information on configuration options.

### Environment variables

- `ARTIFACTS_KEYRING_NONINTERACTIVE_MODE`: Controls whether the underlying credential provider can issue 
interactive prompts.

### Build Environment Variables

- `ARTIFACTS_CREDENTIAL_PROVIDER_RID`: Controls whether or not to build with a specific runtime of the 
self-contained .NET version of the Azure Artifacts Credential Provider.
- `ARTIFACTS_CREDENTIAL_PROVIDER_NON_SC`: Controls whether or not to build the non-self-contained 
.NET 8 version of keyring.

## Local development

1. Install build dependencies with `pip install .`
2. For local builds, build the project using `python -m build --outdir %DIRECTORY%`
3. You can also mimic the CI build using `cibuildwheel --platform auto --output-dir %DIRECTORY%`
4. Open a new terminal window in `%DIRECTORY%`, then run `pip install ***.whl --force-reinstall`

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
