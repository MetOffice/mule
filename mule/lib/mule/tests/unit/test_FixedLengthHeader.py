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
Unit tests for :class:`mule.FixedLengthHeader`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import six
import numpy as np

import mule.tests as tests

from mule import FixedLengthHeader


class Test_empty(tests.MuleTest):
    def test_default(self):
        header = FixedLengthHeader.empty()
        self.assertArrayEqual(header.raw, [None] + [-32768] * 256)


class Test_from_file(tests.MuleTest):
    def test_default(self):
        data = (np.arange(1000) * 10).astype(">i8")
        with self.temp_filename() as filename:
            data.tofile(filename)
            with open(filename, 'rb') as source:
                header = FixedLengthHeader.from_file(source)
        self.assertArrayEqual(header.raw[1:], np.arange(256) * 10)


class Test___init__(tests.MuleTest):
    def test_invalid_length(self):
        with six.assertRaisesRegex(self,
                                   ValueError,
                                   'Incorrect size for fixed length header'):
            FixedLengthHeader(list(range(15)))


def make_header():
    return FixedLengthHeader((np.arange(256) + 1) * 10)


class Test_data_set_format_version(tests.MuleTest):
    def test(self):
        header = make_header()
        self.assertEqual(header.data_set_format_version, 10)


class Test_sub_model(tests.MuleTest):
    def test(self):
        header = make_header()
        self.assertEqual(header.sub_model, 20)


class Test_total_prognostic_fields(tests.MuleTest):
    def test(self):
        header = make_header()
        self.assertEqual(header.total_prognostic_fields, 1530)


class Test_integer_constants_start(tests.MuleTest):
    def test(self):
        header = make_header()
        self.assertEqual(header.integer_constants_start, 1000)


class Test_integer_constants_shape(tests.MuleTest):
    def test(self):
        header = make_header()
        self.assertEqual(header.integer_constants_length, 1010)


class Test_row_dependent_constants_shape(tests.MuleTest):
    def test(self):
        header = make_header()
        self.assertEqual((header.row_dependent_constants_dim1,
                          header.row_dependent_constants_dim2), (1160, 1170))


class Test_data_shape(tests.MuleTest):
    def test(self):
        header = make_header()
        self.assertEqual((header.data_dim1,
                          header.data_dim2), (1610, 1620,))


if __name__ == '__main__':
    tests.main()
