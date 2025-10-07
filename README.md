# gha-tools

[![PyPI - Version](https://img.shields.io/pypi/v/gha-tools.svg)](https://pypi.org/project/gha-tools)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/gha-tools.svg)](https://pypi.org/project/gha-tools)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install gha-tools
```

You can also use `pipx` to directly run `gha-tools`.

## Usage

### Automatically updating workflow action versions

Use `gh-tools autoupdate` on a workflow file or directory to automatically
update the action versions to the latest available version.

* By default, the command will not write changes to the file system; use `--write` to have it do that.
* You can use `--diff` to see what changes would be made. This can be used in conjunction with `--write`.
* You can use `--version-strategy=specific` to update to a specific latest version tag instead of the major
  tag, e.g. `v1.2.3` instead of `v1`.  The default is to use the major tag, when available.

```console
$ gha-tools autoupdate --diff .github/workflows
Updating .github/workflows/publish.yml...
  No changes to .github/workflows/publish.yml.
Updating .github/workflows/ci.yml...
--- .github/workflows/ci.yml
+++ .github/workflows/ci.yml
@@ -34,7 +34,7 @@
             requirements*txt
       - run: 'pip install -e . -r requirements-test.txt'
       - run: py.test -vvv --cov .
-      - uses: codecov/codecov-action@v2
+      - uses: codecov/codecov-action@v3

   Lint:
     runs-on: ubuntu-20.04
```

#### Version pinning

GitHub Actions best practice is to pin the versions of actions to a specific version SHA, as tags may be mutable.
You can use `--pin` to have `gha-tools autoupdate` pin the action to the latest commit SHA for the specified version tag.
If you trust the first-party actions to use immutable tags, use `--pin=third_party`; otherwise use `--pin=all`.

```console
$ gha-tools autoupdate --pin=third_party --diff .github/workflows
Updating .github/workflows/test.yml...
--- .github/workflows/test.yml
+++ .github/workflows/test.yml
@@ -12,13 +12,13 @@
   lint:
     runs-on: ubuntu-latest
     steps:
-      - uses: actions/checkout@v3
-      - uses: akx/pre-commit-uv-action@v0.1.0
+      - uses: actions/checkout@v5
+      - uses: akx/pre-commit-uv-action@19e2cbdb93404ff82f52044f07306443bc0bff7a # v0.1.0
```

## GitHub Rate Limiting

Since this tool uses the GitHub API, you may run into rate limiting issues.
You can specify your GitHub authentication via the environment variable `GITHUB_TOKEN` or `GITHUB_AUTH`.

If the value of the environment variable contains a colon (`:`), it will be interpreted as a username and password;
this is useful with Personal Access Tokens, which are used with your GitHub username.

## License

`gha-tools` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
