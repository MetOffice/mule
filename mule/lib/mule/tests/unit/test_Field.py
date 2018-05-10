# (C) Crown Copyright 2018, Met Office. All rights reserved.
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
Unit tests for :class:`mule.Field`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import mock
import numpy as np

import mule.tests as tests

from mule import Field, _NullReadProvider


class Test_int_headers(tests.MuleTest):
    def test(self):
        field = Field(np.arange(45), list(range(19)), None)
        self.assertArrayEqual(field._lookup_ints, np.arange(45))


class Test_real_headers(tests.MuleTest):
    def test(self):
        field = Field(list(range(45)), np.arange(19), None)
        self.assertArrayEqual(field._lookup_reals, np.arange(19))


class Test_num_values(tests.MuleTest):
    def test_64(self):
        field = Field(list(range(45)), list(range(19)), None)
        self.assertEqual(field.num_values(), 64)

    def test_128(self):
        field = Field(list(range(45)), list(range(83)), None)
        self.assertEqual(field.num_values(), 128)


class Test_get_data(tests.MuleTest):
    def test_None(self):
        field = Field([], [], None)
        self.assertIsNone(field.get_data())

# Disabled because: the functionality to replace the provider with a straight
#                   numpy array no longer exists
#    def test_ndarray(self):
#        data = np.arange(12).reshape(3, 4)
#        field = Field([], [], data)
#        self.assertIs(field.get_data(), data)

# Disabled because: the provider object is slightly stricter now - any class
#                   with a "read_data" method is no longer sufficient
#    def test_provider(self):
#        provider = mock.Mock(read_data=lambda: mock.sentinel.DATA)
#        field = Field([], [], provider)
#        self.assertIs(field.get_data(), mock.sentinel.DATA)

# Disabled because: the functionality to replace the provider with a straight
#                   numpy array no longer exists, and neither does set_data
# class Test_set_data(tests.MuleTest):
#     def test_None(self):
#         data = np.arange(12).reshape(3, 4)
#         field = Field([], [], data)
#         field.set_data(None)
#         self.assertIsNone(field.get_data())

#     def test_ndarray(self):
#         field = Field([], [], None)
#         data = np.arange(12).reshape(3, 4)
#         field.set_data(data)
#         self.assertArrayEqual(field.get_data(), data)

#     def test_provider(self):
#         provider = mock.Mock(read_data=lambda: mock.sentinel.DATA)
#         field = Field([], [], None)
#         field.set_data(provider)
#         self.assertIs(field.get_data(), mock.sentinel.DATA)


class Test__can_copy_deferred_data(tests.MuleTest):
    def _check_formats(self,
                       old_lbpack, new_lbpack,
                       old_bacc=-6, new_bacc=-6,
                       absent_provider=False):

        lookup_entry = mock.Mock(lbpack=old_lbpack, bacc=old_bacc)
        provider = _NullReadProvider(lookup_entry, None, None)
        if absent_provider:
            provider = None
        field = Field(list(range(45)), list(range(19)), provider)
        return field._can_copy_deferred_data(new_lbpack, new_bacc)

    def test_okay_simple(self):
        self.assertTrue(self._check_formats(1234, 1234))

    def test_fail_different_lbpack(self):
        self.assertFalse(self._check_formats(1234, 1238))

    def test_fail_nodata(self):
        self.assertFalse(self._check_formats(1234, 1234, absent_provider=True))

    def test_fail_different_bacc(self):
        self.assertFalse(self._check_formats(1234, 1234, new_bacc=-8))


if __name__ == '__main__':
    tests.main()
