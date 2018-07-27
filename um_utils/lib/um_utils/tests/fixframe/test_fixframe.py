# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of the UM utilities module, which use the Mule API.
#
# Mule and these utilities are free software: you can redistribute it and/or
# modify them under the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# These utilities are distributed in the hope that they will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with these utilities.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""Tests for the fixframe utility in the :mod:`um_utils` module."""

from __future__ import (absolute_import, division, print_function)

import um_utils.tests as tests
from um_utils import fixframe


class _TestFixFrameBase(object):
    """
    Class for testing fixframe function.
    """

    def test_gridfix(self):
        """
        Main test function.  Can be called for either EG or ND case by
        passing the grid staggering and the stagger offset.
        """
        nx, ny, nz = 10, 10, 1
        x0, y0, dx, dy = 0, 0, 0.1, 0.2
        # Create a basic UM file with a mismatch between the field
        # headers and file header
        ff = self._minimal_valid_ff(nx, ny, nz, x0, y0, dx, dy,
                                    self.STAGGERING)
        # Create a second file with a smaller grid
        ny, nx, nz, x0, y0 = 3, 2, 1, 0.2, 0.6
        ff2 = self._minimal_valid_ff(nx, ny, nz, x0, y0, dx, dy,
                                     self.STAGGERING)
        self.new_p_field(ff2)
        # Set stashcode to orography
        ff2.fields[0].lbuser4 = 33
        # Lat/lon grid
        ff2.fields[0].lbcode = 1
        # Add field on smaller grid to file with original grid
        ff.fields.append(ff2.fields[0])
        # Pass into fixframe function
        fixedfile = fixframe.fixframe(ff)
        # Check that the fieldsfile object returned has headers
        # from the smaller grid
        self.assertEqual(y0, fixedfile.real_constants.start_lat)
        self.assertEqual(x0, fixedfile.real_constants.start_lon)
        self.assertEqual(ny, fixedfile.integer_constants.num_rows)
        self.assertEqual(nx, fixedfile.integer_constants.num_cols)


class TestFixFrameND(_TestFixFrameBase, tests.UMUtilsNDTest):
    """
    New Dynamics grid stagger version of fixframe test
    """
    # New Dynamics grid staggering
    STAGGERING = 3


class TestFixFrameEG(_TestFixFrameBase, tests.UMUtilsEGTest):
    """
    ENDGame grid stagger version of fixframe test
    """
    # ENDGame grid staggering
    STAGGERING = 6


if __name__ == "__main__":
    tests.main()
