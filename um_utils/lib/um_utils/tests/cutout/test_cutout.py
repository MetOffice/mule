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
"""Tests for the cutout utilities in the :mod:`um_utils` module."""

from __future__ import (absolute_import, division, print_function)

import os
import numpy as np
import um_utils.tests as tests

from six import StringIO
from um_utils import cutout
from mule.stashmaster import STASHmaster


class _TestCutoutBase(object):
    """
    Base object for cutout tests - to be combined with either the EG or ND
    test classes to produce a valid testing object.

    """
    def run_test(self, VALID_DATA, VALID_HEADS, addfield_method):
        # Create the empty fieldsfile object
        ff = self._minimal_valid_ff(self.DOMAIN_XY_DIMS[0],
                                    self.DOMAIN_XY_DIMS[1],
                                    self.N_LEVELS,
                                    self.DOMAIN_XY_START[0],
                                    self.DOMAIN_XY_START[1],
                                    self.DOMAIN_XY_SPACING[0],
                                    self.DOMAIN_XY_SPACING[1], self.STAGGERING)
        # Set the pole (for cutout) and add a field of the requested type
        ff.real_constants.north_pole_lon = self.DOMAIN_XY_POLE[0]
        ff.real_constants.north_pole_lat = self.DOMAIN_XY_POLE[1]
        ff.fixed_length_header.horiz_grid_type = 0
        addfield_method(ff)

        # Attach stashmaster
        sm = STASHmaster.from_file(tests.SAMPLE_STASHMASTER)
        ff.attach_stashmaster_info(sm)

        # Call cutout (suppressing the output)
        strbuffer = StringIO()
        cutout_method = getattr(cutout, self.CUTOUT_METHOD)
        cutout_ff = cutout_method(ff, *self.CUTOUT_PARAMS, stdout=strbuffer)

        # Extract and test the resulting field object
        field = cutout_ff.fields[0]
        self.assertArrayEqual(field.get_data(), VALID_DATA)
        self.assertEqual(field.lbnpt, VALID_HEADS[0])
        self.assertEqual(field.lbrow, VALID_HEADS[1])
        self.assertEqual(field.bzx, VALID_HEADS[2])
        self.assertEqual(field.bzy, VALID_HEADS[3])

    def test_p_field(self):
        self.run_test(
            self.P_VALID_DATA, self.P_VALID_HEADS, self.new_p_field)

    def test_u_field(self):
        self.run_test(
            self.U_VALID_DATA, self.U_VALID_HEADS, self.new_u_field)

    def test_v_field(self):
        self.run_test(
            self.V_VALID_DATA, self.V_VALID_HEADS, self.new_v_field)

    def test_uv_field(self):
        self.run_test(
            self.UV_VALID_DATA, self.UV_VALID_HEADS, self.new_uv_field)


class TestNDIndexCutout(_TestCutoutBase, tests.UMUtilsNDTest):
    """Test case for New Dynamics file with index based cutout."""
    # The basic setup for the file - a fairly typical Global N48 domain
    DOMAIN_XY_DIMS = (96, 72)
    DOMAIN_XY_SPACING = (3.75, 2.5)
    DOMAIN_XY_START = (0.0, -90.0)
    DOMAIN_XY_POLE = (0.0, 90.0)
    N_LEVELS = 70
    # New Dynamics grid staggering
    STAGGERING = 3

    # The input arguments to cutout - 5x6 area from (3,4)
    CUTOUT_PARAMS = (3, 4, 5, 6)
    CUTOUT_METHOD = "cutout"

    # These arrays store the expected data values from the cutout
    #  - Each row has 96 points, so the 4rd row will start at point
    #        (4 - 1)*96 = 288
    #  - The 3rd point in the row will be
    #        (288 + 3) - 1 = 290
    #  - The subsequent rows are then 96 points ahead of the first
    #    row at all elements (290 + 96 = 386, etc.)
    P_VALID_DATA = [
        [290.0,  291.0,  292.0,  293.0,  294.0],
        [386.0,  387.0,  388.0,  389.0,  390.0],
        [482.0,  483.0,  484.0,  485.0,  486.0],
        [578.0,  579.0,  580.0,  581.0,  582.0],
        [674.0,  675.0,  676.0,  677.0,  678.0],
        [770.0,  771.0,  772.0,  773.0,  774.0],
        ]
    U_VALID_DATA = P_VALID_DATA
    # The V and UV data will have one less row than the P and U data
    V_VALID_DATA = P_VALID_DATA[:-1]
    UV_VALID_DATA = V_VALID_DATA

    # These store the expected values for the size and headers of
    # the output field (lbnpt, lbrow, bzx, bzy)
    P_VALID_HEADS = (5, 6, 3.75, -85.0)
    U_VALID_HEADS = (5, 6, 5.625, -85.0)
    V_VALID_HEADS = (5, 5, 3.75, -83.75)
    UV_VALID_HEADS = (5, 5, 5.625, -83.75)


class TestNDCoordsCutout(TestNDIndexCutout):
    """Test case for New Dynamics file with coords based cutout."""
    # The input arguments to cutout - these have been chosen such that
    # they should cutout exactly the same region as the class above
    # (allowing the valid data to be shared)
    CUTOUT_PARAMS = (7.5, -82.5, 22.5, -70.0)
    CUTOUT_METHOD = "cutout_coords"


class TestEGIndexCutout(_TestCutoutBase, tests.UMUtilsEGTest):
    """Test case for ENDGame file with index based cutout."""
    # The basic setup for the file - a fairly typical Global N48 domain
    DOMAIN_XY_DIMS = (96, 72)
    DOMAIN_XY_SPACING = (3.75, 2.5)
    DOMAIN_XY_START = (0.0, -90.0)
    DOMAIN_XY_POLE = (0.0, 90.0)
    N_LEVELS = 70
    # ENDGame grid staggering
    STAGGERING = 6

    # The input arguments to cutout - 5x6 area from 3,4
    CUTOUT_PARAMS = (3, 4, 5, 6)
    CUTOUT_METHOD = "cutout"

    # These arrays store the expected data values from the cutout
    #  - Each row has 96 points, so the 4rd row will start at point
    #        (4 - 1)*96 = 288
    #  - The 3rd point in the row will be
    #        (288 + 3) - 1 = 290
    #  - The subsequent rows are then 96 points ahead of the first
    #    row at all elements (290 + 96 = 386, etc.)
    V_VALID_DATA = [
        [290.0,  291.0,  292.0,  293.0,  294.0],
        [386.0,  387.0,  388.0,  389.0,  390.0],
        [482.0,  483.0,  484.0,  485.0,  486.0],
        [578.0,  579.0,  580.0,  581.0,  582.0],
        [674.0,  675.0,  676.0,  677.0,  678.0],
        [770.0,  771.0,  772.0,  773.0,  774.0],
        [866.0,  867.0,  868.0,  869.0,  870.0],
        ]
    UV_VALID_DATA = V_VALID_DATA
    # The P and U data will have one less row than the V and UV data
    P_VALID_DATA = V_VALID_DATA[:-1]
    U_VALID_DATA = P_VALID_DATA

    # These store the expected values for the size and headers of
    # the output field (lbnpt, lbrow, bzx, bzy)
    P_VALID_HEADS = (5, 6, 5.625, -83.75)
    U_VALID_HEADS = (5, 6, 1.875, -85.0)
    V_VALID_HEADS = (5, 7, 3.75, -86.25)
    UV_VALID_HEADS = (5, 7, 3.75, -85.0)


class TestEGCoordsCutout(TestEGIndexCutout):
    """Test case for New Dynamics file with coords based cutout."""
    # The input arguments to cutout - these have been chosen such that
    # they should cutout exactly the same region as the class above
    # (allowing the valid data to be shared)
    CUTOUT_PARAMS = (9.375, -81.25, 24.375, -68.75)
    CUTOUT_METHOD = "cutout_coords"


class TestNDGlobalWrap(TestNDIndexCutout):
    """
    Test case for New Dynamics file where cutout area crosses the edge
    of the (wrapping) domain.

    """
    # The input arguments - 6x5 area at the right-centre edge of the domain
    # (since the domain only has 96 points this will wrap to the other side)
    CUTOUT_PARAMS = (94, 30, 6, 5)

    # These arrays store the expected data values from the cutout
    #  - Each row has 96 points, so the 30th row will start at point
    #        (30 - 1)*96 = 2784
    #  - The 94th point in the row will be
    #        (2784 + 94) - 1 = 2877
    #  - The subsequent rows are then 96 points ahead of the first
    #    row at all elements (2877 + 96 = 2973, etc.)
    #  - Note that 3 right-most columns contain the points which follow the
    #    3 left-most columns but shifted down by one row (wrapping)
    P_VALID_DATA = [
        [2877.0, 2878.0, 2879.0, 2784.0, 2785.0, 2786.0],
        [2973.0, 2974.0, 2975.0, 2880.0, 2881.0, 2882.0],
        [3069.0, 3070.0, 3071.0, 2976.0, 2977.0, 2978.0],
        [3165.0, 3166.0, 3167.0, 3072.0, 3073.0, 3074.0],
        [3261.0, 3262.0, 3263.0, 3168.0, 3169.0, 3170.0],
        ]
    U_VALID_DATA = P_VALID_DATA
    # The V and UV data will have one less row than the P and U data
    V_VALID_DATA = P_VALID_DATA[:-1]
    UV_VALID_DATA = V_VALID_DATA

    # These store the expected values for the size and headers of
    # the output field (lbnpt, lbrow, bzx, bzy)
    P_VALID_HEADS = (6, 5, 345.0, -20.0)
    U_VALID_HEADS = (6, 5, 346.875, -20.0)
    V_VALID_HEADS = (6, 4, 345.0, -18.75)
    UV_VALID_HEADS = (6, 4, 346.875, -18.75)


class TestEGGlobalWrap(TestEGIndexCutout):
    """
    Test case for ENDGame file where cutout area crosses the edge
    of the (wrapping) domain.

    """
    # The input arguments - 6x5 area at the right-centre edge of the domain
    # (since the domain only has 96 points this will wrap to the other side)
    CUTOUT_PARAMS = (94, 30, 6, 5)

    # These arrays store the expected data values from the cutout
    #  - Each row has 96 points, so the 30th row will start at point
    #        (30 - 1)*96 = 2784
    #  - The 94th point in the row will be
    #        (2784 + 94) - 1 = 2877
    #  - The subsequent rows are then 96 points ahead of the first
    #    row at all elements (2877 + 96 = 2973, etc.)
    #  - Note that 3 right-most columns contain the points which follow the
    #    3 left-most columns but shifted down by one row (wrapping)
    V_VALID_DATA = [
        [2877.0, 2878.0, 2879.0, 2784.0, 2785.0, 2786.0],
        [2973.0, 2974.0, 2975.0, 2880.0, 2881.0, 2882.0],
        [3069.0, 3070.0, 3071.0, 2976.0, 2977.0, 2978.0],
        [3165.0, 3166.0, 3167.0, 3072.0, 3073.0, 3074.0],
        [3261.0, 3262.0, 3263.0, 3168.0, 3169.0, 3170.0],
        [3357.0, 3358.0, 3359.0, 3264.0, 3265.0, 3266.0],
        ]
    UV_VALID_DATA = V_VALID_DATA
    # The P and U data will have one less row than the V and UV data
    P_VALID_DATA = V_VALID_DATA[:-1]
    U_VALID_DATA = P_VALID_DATA

    # These store the expected values for the size and headers of
    # the output field (lbnpt, lbrow, bzx, bzy)
    P_VALID_HEADS = (6, 5, 346.875, -18.75)
    U_VALID_HEADS = (6, 5, 343.125, -20.0)
    V_VALID_HEADS = (6, 6, 345.0, -21.25)
    UV_VALID_HEADS = (6, 6, 345.0, -20.0)


if __name__ == "__main__":
    tests.main()
