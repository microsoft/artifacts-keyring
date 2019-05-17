# artifacts-keyring
Provides authentication for [Azure DevOps](https://azure.com/devops) via the `keyring` library

This is an extension to [keyring](https://pypi.org/project/keyring), and will automatically be loaded.
Both [pip](https://pypi.org/project/pip) and [twine](https://pypi.org/project/twine) will use `keyring` to
find credentials.

To install this package:

```
pip install artifacts-keyring
```

To use this package through `pip` or `twine`, just provide your repository URL when installing or
uploading to your Azure Artifacts feed.

To use this package directly, use `twine.get_credential` and provide your feed URL as the system
requiring credentials. The username is optional, and the name that should be used will be returned.

# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.microsoft.com.

When you submit a pull request, a CLA-bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., label, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
