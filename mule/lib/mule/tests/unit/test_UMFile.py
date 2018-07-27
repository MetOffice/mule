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
Unit tests for :class:`mule.UMFile`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import six
import os.path
import shutil
import tempfile
import warnings

import mule.tests as tests
from mule.tests import check_common_n48_testdata, COMMON_N48_TESTDATA_PATH


from mule import UMFile


# Do sanity checks for a "minimal" file -- aka a bare fixed-length-header.
def _check_minimal_file(testcase, ffv):
    testcase.assertIsNotNone(ffv.fixed_length_header)
    testcase.assertArrayEqual(ffv.fixed_length_header.raw,
                              [None] + [-32768] * 256)
    testcase.assertIsNone(ffv.integer_constants)
    testcase.assertIsNone(ffv.real_constants)
    testcase.assertIsNone(ffv.level_dependent_constants)
    testcase.assertIsNone(ffv.row_dependent_constants)
    testcase.assertIsNone(ffv.column_dependent_constants)
    testcase.assertEqual(ffv.fields, [])


class Test___init__(tests.MuleTest):
    """Check UMFile __init__ method."""
    def test_missing_file(self):
        dir_path = tempfile.mkdtemp()
        try:
            file_path = os.path.join(dir_path, 'missing')
            with six.assertRaisesRegex(self, IOError, 'No such file'):
                UMFile.from_file(file_path)
        finally:
            shutil.rmtree(dir_path)

    def test_new(self):
        ffv = UMFile()
        self.assertArrayEqual(ffv.fixed_length_header.raw,
                              [None] + [-32768] * 256)
        _check_minimal_file(self, ffv)


class Test_from_file(tests.MuleTest):
    """Checkout different creation routes for the same file."""
    def test_bypath(self):
        ffv = UMFile.from_file(COMMON_N48_TESTDATA_PATH)
        self.assertEqual(type(ffv), UMFile)
        check_common_n48_testdata(self, ffv)

    def test_byfile(self):
        with open(COMMON_N48_TESTDATA_PATH) as open_file:
            ffv = UMFile.from_file(open_file)
        self.assertEqual(type(ffv), UMFile)
        check_common_n48_testdata(self, ffv)


class Test_to_file__targets(tests.MuleTest):
    def test_copy_byfile(self):
        ffv = UMFile.from_file(COMMON_N48_TESTDATA_PATH)
        with self.temp_filename() as temp_path:
            with open(temp_path, 'wb') as temp_file:
                ffv.to_file(temp_file)
            assert os.path.exists(temp_path)
            # Read it back and repeat our basic "known content" tests
            ffv_rb = UMFile.from_file(temp_path)
            check_common_n48_testdata(self, ffv_rb)

    def test_copy_bypath(self):
        ffv = UMFile.from_file(COMMON_N48_TESTDATA_PATH)
        with self.temp_filename() as temp_path:
            ffv.to_file(temp_path)
            assert os.path.exists(temp_path)
            # Read it back and repeat our basic "known content" tests
            ffv_rb = UMFile.from_file(temp_path)
            check_common_n48_testdata(self, ffv_rb)


class Test_to_file__minimal(tests.MuleTest):
    def test_copy_byfile(self):
        ffv = UMFile()
        with self.temp_filename() as temp_path:
            with open(temp_path, 'wb') as temp_file:
                ffv.to_file(temp_file)
            assert os.path.exists(temp_path)
            # Read it back and repeat our basic "known content" tests
            with warnings.catch_warnings():
                msg_exp = r".*Fixed length header does not define.*"
                warnings.filterwarnings("ignore", msg_exp)
                ffv_rb = UMFile.from_file(temp_path)
                _check_minimal_file(self, ffv_rb)


class Test__modifies(tests.MuleTest):
    # TODO: ...
    def test_somefields(self):
        ffv = UMFile.from_file(COMMON_N48_TESTDATA_PATH)
        with self.temp_filename() as temp_path:
            ffv.to_file(temp_path)
            assert os.path.exists(temp_path)
            # Read it back and repeat our basic "known content" tests
            ffv_rb = UMFile.from_file(temp_path)
            check_common_n48_testdata(self, ffv_rb)


class Test_from_template(tests.MuleTest):
    def test_minimal(self):
        ffv = UMFile.from_template({})
        _check_minimal_file(self, ffv)

    def test_component(self):
        test_template = {"integer_constants": {'dims': (12,)}}
        ffv = UMFile.from_template(test_template)
        self.assertEqual(ffv.integer_constants.shape, (12,))

    def test_unknown_component__fail(self):
        test_template = {"junk": {}}
        with six.assertRaisesRegex(
                self,
                ValueError,
                'unrecognised.*component.*("junk")'):
            _ = UMFile.from_template(test_template)

    def test_unsized_component__fail(self):
        test_template = {"integer_constants": {}}
        with six.assertRaisesRegex(self, ValueError,
                                   '"num_words" has no valid default'):
            _ = UMFile.from_template(test_template)


if __name__ == '__main__':
    tests.main()
