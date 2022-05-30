#! /usr/bin/env python3
# This file is part of Dataloop

from setuptools import setup, find_packages
import pathlib
import os

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license_ = f.read()

with open('requirements.txt') as f:
    requirements = f.read()
packages = [
    package for package in find_packages() if package.startswith("dataloop")
]

setup(name='dataloop-upipe',
      version='0.1.9',
      description='Micro Pipelines for Dataloop platform',
      author='Dataloop Team',
      author_email='info@dataloop.ai',
      long_description=readme,
      long_description_content_type='text/markdown',
      packages=find_packages(),
      setup_requires=['wheel'],
      install_requires=requirements,
      python_requires='>=3.8',
      package_data={'upipe': [os.path.relpath(str(p), 'upipe') for p in
                              pathlib.Path('dataloop/upipe/node/server/upipe_viewer').rglob('*')]},
      include_package_data=True,
      )
