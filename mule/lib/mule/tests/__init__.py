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
"""Tests for the :mod:`mule` module."""

from __future__ import (absolute_import, division, print_function)
import six
from six.moves import (filter, input, map, range, zip)  # noqa

import contextlib
import os.path

import numpy as np
import tempfile
import unittest as tests

from mule import Field
import mule.stashmaster

# Override the STASHmaster to pickup the one local to these tests
mule.stashmaster.STASHMASTER_PATH_PATTERN = os.path.join(
    os.path.dirname(__file__), "test_stashmaster")

# Test for availability of mock (which is *not* a standard library at Python 2
# (it was added to the standard library unittest at Python 3)
try:
    if six.PY2:
        import mock
    elif six.PY3:
        import unittest.mock as mock
except ImportError:
    MOCK_AVAILABLE = False
else:
    MOCK_AVAILABLE = True


def skip_mock(fn):
    """
    Decorator which can be used to skip a test if the mock library isn't
    available.  This will completely disable the definition of a method or
    class if it is decorated like this:

    @skip_mock
    def test_which_uses_mock(*args):
        etc

    """
    skip = tests.skipIf(
        condition=not MOCK_AVAILABLE,
        reason="Test required 'mock'")
    return skip(fn)


def _testdata_path():
    """Define the path to the directory containing testing datafiles."""
    # Get the path to directory containing this sourcefile.
    path = os.path.dirname(__file__)
    # Construct the test-data dirpath relative to this.
    testdata_path = os.path.join(path, 'test_datafiles')
    return testdata_path

TESTDATA_DIRPATH = _testdata_path()


def testdata_filepath(relative_path):
    """
    Return the full path to a file in the test-data directory.

    Args:

    * relative_path (string, or sequence of strings):
        path components to combine into a filepath.

    Returns:
        file_path (string)

    .. note::
        No check is made that the file actually exists.

    """
    if not isinstance(relative_path, six.string_types):
        relative_path = os.path.join(*relative_path)
    data_path = os.path.join(TESTDATA_DIRPATH, relative_path)
    return data_path

# Prevent nosetests running this as a test.
testdata_filepath.__test__ = False


class MuleTest(tests.TestCase):
    """An extension of unittest.TestCase with extra test methods."""

    def assertArrayEqual(self, a, b, err_msg=''):
        """Check that numpy arrays have identical contents."""
        np.testing.assert_array_equal(a, b, err_msg=err_msg)

    @contextlib.contextmanager
    def temp_filename(self, suffix=''):
        temp_file = tempfile.mkstemp(suffix)
        os.close(temp_file[0])
        filename = temp_file[1]
        try:
            yield filename
        finally:
            os.remove(filename)

# Define the path to the common load-test data.
COMMON_N48_TESTDATA_PATH = testdata_filepath('n48_multi_field.ff')


# Define basic sanity checks on that specific test datafile.
# For testing alternative load methods.
def check_common_n48_testdata(testcase, ffv):
    # Test for known content properties of a basic test datafile.
    testcase.assertIsNotNone(ffv.integer_constants)
    testcase.assertEqual(ffv.integer_constants.shape, (46,))
    testcase.assertIsNotNone(ffv.real_constants)
    testcase.assertEqual(ffv.real_constants.shape, (38,))
    testcase.assertIsNotNone(ffv.level_dependent_constants)
    testcase.assertIsNone(ffv.row_dependent_constants)
    testcase.assertIsNone(ffv.column_dependent_constants)
    testcase.assertEqual(len(ffv.fields), 5)
    testcase.assertEqual([fld.lbrel for fld in ffv.fields[:-1]],
                         [3, 3, 3, 3])
    testcase.assertEqual(type(ffv.fields[-1]), Field)
    testcase.assertEqual([fld.lbvc for fld in ffv.fields[:-1]],
                         [1, 1, 6, 129])


def main():
    """
    A wrapper that just calls unittest.main().

    Allows mule.tests to be imported in place of unittest, in simple cases.

    """
    tests.main()
