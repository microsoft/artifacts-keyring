# azure-devops-keyring
Provides authentication for [Azure DevOps](https://azure.com/devops) via the `keyring` library

This is an extension to [keyring](https://pypi.org/project/keyring), and will automatically be loaded.
Both [pip](https://pypi.org/project/pip) and [twine](https://pypi.org/project/twine) will use `keyring` to
find credentials.

To install this package:

```
pip install azure-devops-keyring
```

To use this package through `pip` or `twine`, just provide your repository URL when installing or
uploading to your Azure Artifacts feed.

To use this package directly, use `twine.get_credential` and provide your feed URL as the system
requiring credentials. The username is optional, and the name that should be used will be returned.
