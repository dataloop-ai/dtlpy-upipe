#! /usr/bin/env python3
# This file is part of DTLPY.
#
# MICROPIPELINES is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MICROPIPELINES is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MICROPIPELINES.  If not, see <http://www.gnu.org/licenses/>.

from setuptools import setup, find_packages

with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license_ = f.read()

with open('requirements.txt') as f:
    requirements = f.read()

setup(name='micropipelines',
      version='0.1.5',
      description='Micro Pipelines for Dataloop platform',
      author='Eran Shlomo',
      author_email='eran@dataloop.ai',
      license='Apache License 2.0',
      long_description=readme,
      long_description_content_type='text/markdown',
      packages=find_packages(exclude=('tests', 'docs', 'samples')),
      setup_requires=['wheel'],
      install_requires=requirements,
      python_requires='>=3.5.4',
      include_package_data=True,
      )