from setuptools import setup

from guacli import __version__ as version

setup(name = 'guacli',
    version = version,
    description = 'Python client (library and CLI) for Apache Guacamole front-end REST API.',
    keywords="cli client guacamole api",
    url = 'https://github.com/chaimeleon-eu/guacamole-python-client',
    license = "Apache 2.0",
    author = 'Pau Lozano',
    author_email = '',
    packages = [ 'guacli' ],
#   install_requires = [ "argparse"],
    entry_points = {
        "console_scripts": ["guacli = guacli.cli:main"],
    },
)
