# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of the SHUMlib packing library module.
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
# along with this SHUMlib packing module.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""
Unit tests for :mod:`um_packing` module.

"""

from __future__ import (absolute_import, division, print_function)

import sys
import numpy as np

import um_packing.tests as tests
from um_packing import wgdos_unpack, wgdos_pack


def get_random_data(mdi):
    # Returns some random test data to use for the testing
    array = np.random.random((500, 700))
    # Lower the precision of the data a bit
    array = (array*10**5).astype("int")/10.0**2

    # Ensure the test data has some rows with blocks of MDI values
    array[350:400, 150:200] = mdi
    array[350:400, 500:550] = mdi

    # And a block of zeros
    array[200:250, 150:550] = 0.0

    return array


class Test_packing(tests.UMPackingTest):
    # Values of missing data and accuracy to use
    MDI = -1.23456789
    ACCURACY = -10

    def test_1_pack(self):
        # The first test packs the array
        array = get_random_data(self.MDI)
        packed_bytes = wgdos_pack(array, self.MDI, self.ACCURACY)

        return array, packed_bytes

    def test_2_unpack(self):
        # The second test unpacks it again and checks that the degradation
        # in accuracy is within the expected amount it should be
        array, packed_bytes = self.test_1_pack()

        unpacked_array = wgdos_unpack(packed_bytes, self.MDI)

        self.assertArrayLess(np.abs(array - unpacked_array),
                             (2**self.ACCURACY)/2)

        return unpacked_array

    def test_3_repack_and_unpack(self):
        # The third test re-packs the data and then unpacks it once again,
        # but this time the data should be exactly the same afterwards
        unpacked_array = self.test_2_unpack()

        packed_bytes = wgdos_pack(unpacked_array, self.MDI, self.ACCURACY)

        reunpacked_array = wgdos_unpack(packed_bytes, self.MDI)

        self.assertArrayEqual(np.abs(unpacked_array - reunpacked_array), 0.0)

if __name__ == "__main__":
    tests.main()
