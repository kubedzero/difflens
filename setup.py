import setuptools


# https://setuptools.readthedocs.io/en/latest/userguide/declarative_config.html
# From https://packaging.python.org/tutorials/packaging-projects/#configuring-metadata
setuptools.setup(
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#packages
    packages=setuptools.find_packages(),
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#entry-points
    entry_points={"console_scripts": ["difflens = difflens.run:main"]},
    # https://packaging.python.org/guides/distributing-packages-using-setuptools/#install-requires
    # NOTE: The Pipfile is for setting up the build/dev env while install_requires tells Pip what dependencies
    # are also needed when installing this .whl from a package index
    # https://medium.com/expedia-group-tech/simplifying-python-builds-74e76802444f
    # https://stackoverflow.com/questions/49496994 potential alternate methods of auto-syncing from Pipfile
    install_requires=["blake3~=0.1.8", "pandas~=1.2.3", "psutil~=5.8.0"]
)
