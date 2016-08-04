# (C) Crown Copyright 2016, Met Office. All rights reserved.
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

from glob import glob
from setuptools import setup

setup(name='um_utils',
      version='1.3',
      description='Unified Model Fields File utilities',
      author='UM Systems Team',
      url='https://code.metoffice.gov.uk/trac/um',
      package_dir={'': 'lib'},
      packages=['um_utils',
                'um_utils.tests',
                'um_utils.tests.pumf',
                'um_utils.tests.summary',
                'um_utils.tests.cumf',
                'um_utils.tests.cutout',
                'um_utils.tests.fixframe'
                ],
      data_files=[('um_utils/tests', ["lib/um_utils/tests/test_stashmaster"]),
                  ('um_utils/tests/pumf/output',
                   glob('lib/um_utils/tests/pumf/output/*.txt')),
                  ('um_utils/tests/summary/output',
                   glob('lib/um_utils/tests/summary/output/*.txt')),
                  ('um_utils/tests/cumf/output',
                   glob('lib/um_utils/tests/cumf/output/*.txt'))],
      entry_points={
          'console_scripts': [
              'mule-pumf = um_utils.pumf:_main',
              'mule-summary = um_utils.summary:_main',
              'mule-cumf = um_utils.cumf:_main',
              'mule-cutout = um_utils.cutout:_main',
              'mule-trim = um_utils.trim:_main',
              'mule-version = um_utils.version:_main',
              'mule-fixframe = um_utils.fixframe:_main',
              ]})
