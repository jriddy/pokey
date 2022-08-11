# TODO: remove this and switch to poetry or pants
from pathlib import Path

import setuptools

setuptools.setup(
    name="pokey",
    version="0.1.0dev",
    install_requires=[x.strip() for x in Path("requirements.txt").open("rt")],
)
