#!/usr/bin/env python
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************

"""
Unit tests for :mod:`um_packing` module.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import sys
import numpy as np

import um_packing.tests as tests
from um_packing import wgdos_unpack, wgdos_pack

class Test_packing(tests.UMPackingTest):
    def test_packing(self):
        # Generate an array populated by random values
        array = np.random.random((500, 700))

        # These are between 0.0 and 1.0; scale this up by 1000 and reduce
        # to 2 decimal places 
        array = (array*10**5).astype("int")/10.0**2

        # mdi and accuracy values
        mdi = -1.23456789
        accuracy = -10

        # Insert some random blocks of mdi values into the data
        array[350:400, 150:200] = mdi
        array[350:400, 500:550] = mdi

        # Insert a random block of zeros as well
        array[200:250, 150:550] = 0.0

        # Use the packing library to pack the data
        packed_bytes = wgdos_pack(array, mdi, accuracy)

        # Unpack the array again
        unpacked_array = wgdos_unpack(packed_bytes, mdi)

        # The result should be less than half of 2**accuracy different (but it
        # will be different since it is a lossy compression and regardless of
        # accuracy settings the values will be rounded to exact powers of 2)
        self.assertArrayLess(np.abs(array - unpacked_array),
                             (2**accuracy)/2)

        # Re-pack the data
        packed_bytes = wgdos_pack(unpacked_array, mdi, accuracy)

        # And re-unpack it
        reunpacked_array = wgdos_unpack(packed_bytes, mdi)

        # Packing and re-packing the data a second time should produce a result
        # which is exactly identical; since the values are already powers of two
        # following the first packing above
        self.assertArrayEqual(np.abs(unpacked_array - reunpacked_array), 0.0)


if __name__ == "__main__":
    tests.main()

