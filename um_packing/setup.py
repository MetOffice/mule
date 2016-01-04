# (C) Crown Copyright 2016, Met Office. All rights reserved.
#
# This file is part of the UM packing library module.
#
# It is free software: you can redistribute it and/or modify it under
# the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# Mule is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with this UM packing module.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
import setuptools
import numpy as np

setuptools.setup(name='um_packing',
      version='1.0',
      description='Unified Model packing library extension',
      author='UM Systems Team',
      url='https://code.metoffice.gov.uk/trac/um',
      package_dir = {'': 'lib'},
      packages=['um_packing',
                'um_packing.tests'],
      features={
          'packing': setuptools.Feature(
              "UM Packing library (requires UM Licence)",
              standard=True,
              ext_modules=[
                  setuptools.Extension(
                      'um_packing.um_packing',
                      ['lib/um_packing/um_packing.c'],
                      include_dirs=[np.get_include()],
                      )
                  ]
              )
          },      
     )

