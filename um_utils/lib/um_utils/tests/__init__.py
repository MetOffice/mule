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
"""Tests for the :mod:`um_utils` module."""

from __future__ import (absolute_import, division, print_function)

import os
import numpy as np
import unittest as tests

import mule

from mule.stashmaster import STASHmaster

# Path to a simple STASHmaster file sufficient to test the below classes
SAMPLE_STASHMASTER = os.path.join(
    os.path.dirname(__file__), "test_stashmaster")


class _UMUtilsTest(tests.TestCase):
    """
    Base class for test which require the ability to generate a sample
    fields-file object to run.

    """
    def assertArrayEqual(self, a, b, err_msg=''):
        """Check that numpy arrays have identical contents."""
        np.testing.assert_array_equal(a, b, err_msg=err_msg)

    def assertArrayLess(self, a, b, err_msg=''):
        """Check that numpy array is less than value."""
        np.testing.assert_array_less(a, b, err_msg=err_msg)

    def assertLinesEqual(self, line1, line2):
        """Check two output lines are equal."""
        self.assertEqual(line1, line2, "Lines not equal:\nFound:\n  "
                         "'{0}'\nExpected:\n  '{1}'".format(line1, line2))

    @staticmethod
    def _minimal_valid_ff(num_cols, num_rows, num_levels,
                          start_lon, start_lat, col_spacing, row_spacing,
                          grid_stagger):
        """
        Return a basic field-file object; populating the bare minimum header
        inputs for validation.

        """
        ff = mule.FieldsFile()

        ff.fixed_length_header.dataset_type = 3
        ff.fixed_length_header.grid_staggering = grid_stagger

        ff.integer_constants = mule.ff.FF_IntegerConstants.empty()
        ff.integer_constants.num_cols = num_cols
        ff.integer_constants.num_rows = num_rows
        ff.integer_constants.num_p_levels = num_levels

        ff.real_constants = mule.ff.FF_RealConstants.empty()
        ff.real_constants.start_lon = start_lon
        ff.real_constants.start_lat = start_lat
        ff.real_constants.col_spacing = col_spacing
        ff.real_constants.row_spacing = row_spacing

        ff.level_dependent_constants = (
            mule.ff.FF_LevelDependentConstants.empty(num_levels + 1))
        ldc_range = np.arange(num_levels + 1)
        for idim in range(1, ff.level_dependent_constants.shape[1] + 1):
            ff.level_dependent_constants.raw[:, idim] = ldc_range*idim

        stashmaster = STASHmaster.from_file(SAMPLE_STASHMASTER)
        ff.stashmaster = stashmaster

        return ff

    @staticmethod
    def _minimal_valid_field(num_cols, num_rows, start_lon, start_lat,
                             col_spacing, row_spacing):
        """
        Return a basic field object; populating the bare minimum header
        inputs for validation.

        """
        fld = mule.Field3.empty()
        fld.lbrel = 3
        fld.raw[1] = 1
        fld.lbext = 0
        fld.lbnpt, fld.lbrow = num_cols, num_rows
        fld.bdx, fld.bdy = col_spacing, row_spacing

        # Note: the lookup header grid origin holds the "0th" point not
        # the first point (as in the file object grid origin)
        fld.bzx = start_lon - fld.bdx
        fld.bzy = start_lat - fld.bdy

        # Attach a basic range array (reshaped) to be the data
        data = np.arange(fld.lbnpt*fld.lbrow).reshape(fld.lbrow, fld.lbnpt)
        provider = mule.ArrayDataProvider(data)
        fld.set_data_provider(provider)

        return fld


class UMUtilsNDTest(_UMUtilsTest):
    """
    Class for test cases which require the ability to generate a ND
    (New Dynamics) file object.

    """
    def new_p_field(self, ff):
        """
        Append a P field to the given FieldsFile object.  For ND grids the
        P field's origin is at the same point as the file's origin, so no
        adjustment is needed.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(nx, ny, zx, zy, dx, dy)
        # Use a suitable P grid STASH field
        fld.lbuser4 = 4
        ff.fields.append(fld)

    def new_u_field(self, ff):
        """
        Append a U field to the given FieldsFile object.  For ND grids the
        U field's origin is half a grid spacing ahead of the basic/P field
        in the X direction.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(nx, ny, zx + dx/2.0, zy, dx, dy)
        # Use a suitable U grid STASH field
        fld.lbuser4 = 2
        ff.fields.append(fld)

    def new_v_field(self, ff):
        """
        Append a V field to the given FieldsFile object.  For ND grids the
        V field's origin is half a grid spacing ahead of the basic/P field
        in the Y direction, and it contains one less row.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(nx, ny - 1, zx, zy + dy/2.0, dx, dy)
        # Use a suitable V grid STASH field
        fld.lbuser4 = 3
        ff.fields.append(fld)

    def new_uv_field(self, ff):
        """
        Append a UV field to the given FieldsFile object.  For ND grids the
        UV field's origin is half a grid spacing ahead of the basic/P field
        in both directions, and it contains one less row.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(
            nx, ny - 1, zx + dx/2.0, zy + dy/2.0, dx, dy)
        # Use a suitable UV grid STASH field
        fld.lbuser4 = 3227
        ff.fields.append(fld)


class UMUtilsEGTest(_UMUtilsTest):
    """
    Class for test cases which require the ability to generate an EG
    (ENDGame) file object.

    """
    def new_p_field(self, ff):
        """
        Append a P field to the given FieldsFile object.  For EG grids the
        P field's origin is half a grid spacing ahead of the basic field
        in both directions.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(
            nx, ny, zx + dx/2.0, zy + dy/2.0, dx, dy)
        # Use a suitable P grid STASH field
        fld.lbuser4 = 4
        ff.fields.append(fld)

    def new_u_field(self, ff):
        """
        Append a U field to the given FieldsFile object.  For EG grids the
        U field's origin is half a grid spacing behind the basic/P field
        in the X direction.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(nx, ny, zx - dx/2.0, zy, dx, dy)
        # Use a suitable U grid STASH field
        fld.lbuser4 = 2
        ff.fields.append(fld)

    def new_v_field(self, ff):
        """
        Append a V field to the given FieldsFile object.  For EG grids the
        V field's origin is half a grid spacing behind the basic/P field
        in the Y direction, and it contains one extra row.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(nx, ny + 1, zx, zy - dy/2.0, dx, dy)
        # Use a suitable V grid STASH field
        fld.lbuser4 = 3
        ff.fields.append(fld)

    def new_uv_field(self, ff):
        """
        Append a UV field to the given FieldsFile object.  For EG grids the
        UV field's origin is at the same point as the basic/P field, but
        it contains one extra row.

        """
        nx, ny = ff.integer_constants.num_cols, ff.integer_constants.num_rows
        zx, zy = ff.real_constants.start_lon, ff.real_constants.start_lat
        dx, dy = ff.real_constants.col_spacing, ff.real_constants.row_spacing
        fld = self._minimal_valid_field(nx, ny + 1, zx, zy, dx, dy)
        # Use a suitable UV grid STASH field
        fld.lbuser4 = 3227
        ff.fields.append(fld)


def main():
    """
    A wrapper that just calls unittest.main().

    Allows um_packing.tests to be imported in place of unittest

    """
    tests.main()
