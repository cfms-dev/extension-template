# Official Extension Template for CFMS

[![Copier](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/copier-org/copier/master/img/badge/badge-grayscale-inverted-border.json)](https://github.com/copier-org/copier)

This is a template designed for the development of server-side extensions for CFMS on Websocket projects; it enables the quick creation of new extension projects using `copier` and offers built-in, robust support for server-side integration testing.

## Usage

If `copier` have not been installed yet:

```bash
uv tool install --with jinja2-shell-extension copier
```

Run:

```bash
copier copy gh:cfms-dev/extension-template {your_destination} --trust
```

The `--trust` parameter allows the execution of code designed to automatically detect the author's name and email from the Git configuration and populate them directly into the target project's `pyproject.toml`.

To create your project, you will be asked a few simple questions, including the extension slug, identifier, and so on.
