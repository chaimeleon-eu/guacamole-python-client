# guacli

A python client (library and CLI) for the Apache Guacamole front-end REST API.

## Requirements

Tested with python 3.10.2 and 3.6.9.

## Install

```
pip install guacli
```

## Example of use

```
guacli --help
guacli --url "https://example.com/guacamole" --user guacadmin create user james-smith
```

## Upgrade

```
pip install --upgrade guacli
```

## Uninstall

```
pip uninstall guacli
```

## Manually install

```
cd /opt
git clone https://github.com/chaimeleon-eu/guacamole-python-client.git
mv guacamole-python-client/guacli/cli.py guacamole-python-client/cli
chmod +x guacamole-python-client/cli
ln -s /opt/guacamole-python-client/cli /usr/local/bin/guacli
```

## For developers

### Run without install

```
python -m guacli.cli --help
```

### Test setup

Test the setup.py:
```
pip install --log install.log .
```
Uninstall with:
```
pip uninstall guacli
```

### Build the package

REF: https://packaging.python.org/en/latest/tutorials/packaging-projects/

Requirements:
```
python -m pip install --upgrade build
python -m pip install --upgrade twine
```

Build:
```
cd guacamole-python-client
python -m build
ls dist
```
Two files are generated: 
 - guacli-VERSION.tar-gz is the source package
 - guacli-VERSION-py3-none-any.whl is the built package

Then upload the package:
```
python -m twine upload dist/*
```
If you want to test previously, add `--repository testpypi` for uploading to test.pypi.org.

