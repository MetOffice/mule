# (C) Crown Copyright 2018, Met Office. All rights reserved.
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
# along with this UM SST-pert module.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
import setuptools
import numpy as np

setuptools.setup(
    name='um_sstpert',
    version='2017.08.1',
    description='Unified Model SST-perturbation extension and utility',
    author='UM Systems Team',
    url='https://code.metoffice.gov.uk/trac/um',
    package_dir={'': 'lib'},
    packages=['um_sstpert'],
    features={
        'sstpert': setuptools.Feature(
            "UM SST-pert library (requires UM Licence)",
            standard=True,
            ext_modules=[
                setuptools.Extension(
                    'um_sstpert.um_sstpert',
                    ['lib/um_sstpert/um_sstpert.c'],
                    include_dirs=[np.get_include()],
                    libraries=["um_sstpert",
                               "shum_string_conv"])
                ])},
    entry_points={
        'console_scripts': [
            'mule-sstpert = um_sstpert:_main',
            ]})
