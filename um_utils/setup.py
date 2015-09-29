# (C) Crown Copyright 2015, Met Office. All rights reserved.
#
# This file is part of Mule.
#
# Mule is free software: you can redistribute it and/or modify it under
# the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# Mule is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with Mule.  If not, see <http://opensource.org/licenses/BSD-3-Clause>.

from setuptools import setup

setup(name='um_utils',
      version='1.0',
      description='Unified Model Fields File utilities',
      author='UM Systems Team',
      url='https://code.metoffice.gov.uk/trac/um',
      package_dir = {'': 'lib'},
      packages=['um_utils',
                'um_utils.tests',])

