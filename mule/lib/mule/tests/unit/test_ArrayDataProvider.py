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
Unit tests for :class:`mule.ArrayDataProvider`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import six
import numpy as np
import numpy.ma

import mule.tests as tests

from mule import ArrayDataProvider, Field


class Test_ArrayDataProvider___init__(tests.MuleTest):
    def test_basic_array(self):
        array = [[1.2, 2.3, 3.4, 5.6], [6., 7., 8., 9.]]
        array = np.array(array)
        adp = ArrayDataProvider(array)
        result = adp._data_array()
        self.assertIs(result, array)

    def test_cast(self):
        array = [[1.2, 2.3, 3.4, 5.6], [6., 7., 8., 9.]]
        adp = ArrayDataProvider(array)
        result = adp._data_array()
        self.assertIsInstance(result, np.ndarray)
        self.assertArrayEqual(result, array)

    def test_ints(self):
        array = np.array([[1, 17], [4, 32]], dtype=np.int32)
        adp = ArrayDataProvider(array)
        result = adp._data_array()
        self.assertArrayEqual(result, array)
        self.assertEqual(result.dtype, np.int32)

    def test_masked_nomask(self):
        array = [[1.2, 2.3, 3.4], [6., 7., 8.]]
        array = np.ma.masked_array(array, mask=[[0, 0, 0], [0, 0, 0]])
        self.assertTrue(isinstance(array, np.ma.MaskedArray))
        adp = ArrayDataProvider(array)
        result = adp._data_array()
        self.assertFalse(isinstance(result, np.ma.MaskedArray))
        self.assertArrayEqual(result, array)

    def test_masked_withmask__fail(self):
        array = [[1.2, 2.3, 3.4], [6., 7., 8.]]
        array = np.ma.masked_array(array, mask=[[0, 1, 0], [0, 0, 0]])
        with six.assertRaisesRegex(self,
                                   ValueError,
                                   'not handle masked data'):
            _ = ArrayDataProvider(array)

    def test_non2d_fail(self):
        array = np.zeros((5,))
        with six.assertRaisesRegex(self,
                                   ValueError,
                                   '(5,).*not 2-dimensional'):
            _ = ArrayDataProvider(array)


class Test_ArrayDataProvider__as_payload(tests.MuleTest):
    def test_basic(self):
        array = [[1.2, 2.3, 3.4, 5.6], [6., 7., 8., 9.]]
        array = np.array(array)
        adp = ArrayDataProvider(array)
        fld = Field(int_headers=[0], real_headers=[0.0], data_provider=adp)
        self.assertIs(fld.get_data(), array)


if __name__ == '__main__':
    tests.main()
