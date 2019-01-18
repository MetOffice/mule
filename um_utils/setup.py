# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
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

import os
import shutil
from glob import glob
import setuptools


class CleanCommand(setuptools.Command):
    """
    Custom clean which gets rid of build files that the
    standard clean command does not
    """
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        for cleanpath in ["./build", "./dist", "./lib/*.egg-info"]:
            print("Removing: {0}...".format(cleanpath))
            cleanpath = glob(cleanpath)
            if cleanpath:
                shutil.rmtree(cleanpath[0])

setuptools.setup(
      name='um_utils',
      version='2019.01.1',
      description='Unified Model Fields File utilities',
      author='UM Systems Team',
      url='https://code.metoffice.gov.uk/trac/um',
      cmdclass={'clean': CleanCommand},
      package_dir={'': 'lib'},
      packages=['um_utils',
                'um_utils.tests',
                'um_utils.tests.pumf',
                'um_utils.tests.select',
                'um_utils.tests.summary',
                'um_utils.tests.cumf',
                'um_utils.tests.cutout',
                'um_utils.tests.fixframe'
                ],
      package_data={'um_utils':
                    [os.path.relpath(path, "lib/um_utils")
                     for path in (glob('lib/um_utils/tests/cumf/output/*') +
                                  glob('lib/um_utils/tests/pumf/output/*') +
                                  glob('lib/um_utils/tests/summary/output/*') +
                                  ['lib/um_utils/tests/test_stashmaster'])]},
      entry_points={
          'console_scripts': [
              'mule-pumf = um_utils.pumf:_main',
              'mule-summary = um_utils.summary:_main',
              'mule-cumf = um_utils.cumf:_main',
              'mule-cutout = um_utils.cutout:_main',
              'mule-trim = um_utils.trim:_main',
              'mule-version = um_utils.version:_main',
              'mule-fixframe = um_utils.fixframe:_main',
              'mule-unpack = um_utils.unpack:_main',
              'mule-select = um_utils.select:_main'
              ]})
