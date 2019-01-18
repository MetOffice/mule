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
import setuptools
from glob import glob


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
    name='mule',
    version='2019.01.1',
    description='Unified Model Fields File interface',
    author='UM Systems Team',
    url='https://code.metoffice.gov.uk/trac/um',
    cmdclass={'clean': CleanCommand},
    package_dir={'': 'lib'},
    packages=['mule',
              'mule.tests',
              'mule.tests.unit',
              'mule.tests.integration',
              'mule.example_code'],
    package_data={'mule':
                  [os.path.relpath(path, "lib/mule")
                   for path in (glob('lib/mule/tests/test_datafiles/*') +
                                ['lib/mule/tests/test_stashmaster'])]})
