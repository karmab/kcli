# Contribution to codebase
if you want to contribute, just do it, live your life!

# Contribution to documentation
Whenever you spot issue in the documentation, don't hesitate to make the change. The documenation is done in `docs/index.md` and to render it fine for [readthedocs.io](https://kcli.readthedocs.io) platform, it needs to be converted to `rst` format.

For this the following command is useful.

```
pandoc --from=markdown --to=rst index.md -o index.rst --columns=400
```
