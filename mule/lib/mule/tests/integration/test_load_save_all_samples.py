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
"""
Integration tests for all :class:`mule` loading methods, on all datafiles.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import warnings
from glob import glob
import os
import os.path

import mule.tests as tests
from mule import UMFile, FieldsFile, LBCFile, AncilFile, DumpFile, load_umfile

# Suppress the warning about the STASHmaster (one of the tested files is
# an ancil which doesn't set the UM version and so will issue this warning)
warnings.filterwarnings("ignore", r".*No STASHmaster file loaded.*")

# Identify all the test datafiles, their types and name stems.
TESTFILE_PATHS = glob(os.path.join(tests.TESTDATA_DIRPATH, '*'))
TESTFILE_TYPES = [path.split('.')[-1] for path in TESTFILE_PATHS]
TESTFILE_NAMES = [os.path.basename(path).split('.')[0]
                  for path in TESTFILE_PATHS]


# Define some quick sanity checks specific to actual recognised files.
def _check_n48_multi_field(testcase, ffv):
    testcase.assertEqual(ffv.level_dependent_constants.shape, (71, 8))
    testcase.assertEqual(len(ffv.fields), 5)
    testcase.assertIsNone(ffv.row_dependent_constants)
    testcase.assertIsNone(ffv.column_dependent_constants)


def _check_eg_boundary_sample(testcase, ffv):
    testcase.assertEqual(ffv.level_dependent_constants.shape, (39, 4))
    testcase.assertEqual(len(ffv.fields), 10)
    testcase.assertIsNone(ffv.row_dependent_constants)
    testcase.assertIsNone(ffv.column_dependent_constants)


def _check_n48_eg_regular_sample(testcase, ffv):
    testcase.assertEqual(ffv.level_dependent_constants.shape, (71, 8))
    testcase.assertEqual(len(ffv.fields), 10)
    testcase.assertIsNone(ffv.row_dependent_constants)
    testcase.assertIsNone(ffv.column_dependent_constants)


def _check_ukv_eg_variable_sample(testcase, ffv):
    testcase.assertEqual(ffv.level_dependent_constants.shape, (71, 8))
    testcase.assertEqual(len(ffv.fields), 1)
    testcase.assertEqual(ffv.row_dependent_constants.shape, (929, 2))
    testcase.assertEqual(ffv.column_dependent_constants.shape, (744, 2))


def _check_soil_params(testcase, ffv):
    testcase.assertEqual(len(ffv.fields), 11)
    testcase.assertIsNone(ffv.row_dependent_constants)
    testcase.assertIsNone(ffv.column_dependent_constants)


def _check_n48_eg_dump_special(testcase, ffv):
    testcase.assertEqual(ffv.level_dependent_constants.shape, (71, 8))
    testcase.assertEqual(len(ffv.fields), 2)
    testcase.assertIsNone(ffv.row_dependent_constants)
    testcase.assertIsNone(ffv.column_dependent_constants)


# Store the sanity-checks by datafile name
KNOWN_EXPECTED_PROPERTIES = {
    'n48_multi_field':  _check_n48_multi_field,
    'eg_boundary_sample': _check_eg_boundary_sample,
    'n48_eg_regular_sample': _check_n48_eg_regular_sample,
    'ukv_eg_variable_sample': _check_ukv_eg_variable_sample,
    'soil_params': _check_soil_params,
    'n48_eg_dump_special': _check_n48_eg_dump_special,
}

# Map file extensions to UMFile subclasses.
_UM_FILE_TYPES = {'dump': DumpFile,
                  'ff': FieldsFile,
                  'lbc': LBCFile,
                  'anc': AncilFile,
                  'pp': None}


class Test_all_sample_data(tests.MuleTest):
    def _file_specific_check(self, name, ffv):
        # Call the file-specific tester function for this file (if known).
        if name not in KNOWN_EXPECTED_PROPERTIES:
            msg = 'unrecognised datafile ? : {}'
            print(msg.format(name))
        else:
            KNOWN_EXPECTED_PROPERTIES[name](self, ffv)

    def test_um_loadsave_all(self):
        # Check each test datafile can load with 'load_umfile' and re-save.
        for path, name, filetype in zip(TESTFILE_PATHS,
                                        TESTFILE_NAMES,
                                        TESTFILE_TYPES):
            # Skip the pp files (they don't work the same at all)
            if filetype == "pp":
                continue

            # Test load_umfile the file.
            ffv = load_umfile(path)

            # Check it loaded with the expected type.
            self.assertEqual(type(ffv), _UM_FILE_TYPES[filetype])

            # Check against expected properties.
            self._file_specific_check(name, ffv)

            # Check you can then save it.
            with self.temp_filename() as temp_filepath:
                ffv.to_file(temp_filepath)

    def test_specific_load_all(self):
        # Check each datafile will load as the expected specific type.
        for path, name, filetype in zip(TESTFILE_PATHS,
                                        TESTFILE_NAMES,
                                        TESTFILE_TYPES):
            # Skip the pp files (they don't work the same at all)
            if filetype == "pp":
                continue

            # Check you can load it as the expected specific type.
            typeclass = _UM_FILE_TYPES.get(filetype)
            if not typeclass:
                msg = 'unrecognised file extension ? : {}'
                raise ValueError(msg.format(filetype))

            ffv = typeclass.from_file(path)

    def test_generic_load_all(self):
        # Check each datafile will load as UMFile, and still look the same.
        for path, name, filetype in zip(TESTFILE_PATHS,
                                        TESTFILE_NAMES,
                                        TESTFILE_TYPES):

            # Skip the pp files (they don't work the same at all)
            if filetype == "pp":
                continue

            # Check you can load it as a generic UMFile.
            ffv = UMFile.from_file(path)

            typeclass = _UM_FILE_TYPES.get(filetype)
            if not typeclass:
                msg = 'unrecognised file extension ? : {}'
                raise ValueError(msg.format(filetype))

            # Check you can save it, and it loads back as the expected type.
            with self.temp_filename() as temp_filepath:
                ffv.to_file(temp_filepath)
                _ = typeclass.from_file(temp_filepath)
                # For good measure, check it still looks as expected, .
                self._file_specific_check(name, ffv)


if __name__ == '__main__':
    tests.main()
