# (C) Crown Copyright 2016, Met Office. All rights reserved.
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
Unit tests for :class:`mule.lbc.LBCFile`.

"""

from __future__ import (absolute_import, division, print_function)

import numpy as np

import mule.tests as tests
from mule import LBCFile, Field3, ArrayDataProvider
from mule.lbc import (LBC_IntegerConstants, LBC_RealConstants,
                      LBC_LevelDependentConstants, LBC_RowDependentConstants,
                      LBC_ColumnDependentConstants, LBCToMaskedArrayOperator,
                      MaskedArrayToLBCOperator)
from mule.validators import ValidateError


class Test___init__(tests.MuleTest):
    """Check LBCFile __init__ method."""
    def test_new_lbcfile(self):
        lbc = LBCFile()
        self.assertArrayEqual(lbc.fixed_length_header.raw,
                              [None] + [-32768] * 256)

        self.assertIsNone(lbc.integer_constants)
        self.assertIsNone(lbc.real_constants)
        self.assertIsNone(lbc.level_dependent_constants)
        self.assertIsNone(lbc.row_dependent_constants)
        self.assertIsNone(lbc.column_dependent_constants)
        self.assertEqual(lbc.fields, [])


class Test_from_file(tests.MuleTest):
    """Checkout different creation routes for the same file."""
    def test_read_lbcfile(self):
        lbc = LBCFile.from_file(
            tests.testdata_filepath("eg_boundary_sample.lbc"))
        self.assertEqual(type(lbc), LBCFile)
        self.assertIsNotNone(lbc.integer_constants)
        self.assertEqual(lbc.integer_constants.shape, (46,))
        self.assertIsNotNone(lbc.real_constants)
        self.assertEqual(lbc.real_constants.shape, (38,))
        self.assertIsNotNone(lbc.level_dependent_constants)
        self.assertEqual(lbc.level_dependent_constants.shape, (39, 4))
        self.assertIsNone(lbc.row_dependent_constants)
        self.assertIsNone(lbc.column_dependent_constants)
        self.assertEqual(len(lbc.fields), 10)
        self.assertEqual([fld.lbrel for fld in lbc.fields[:-1]], [3]*9)
        self.assertEqual([fld.lbvc for fld in lbc.fields[:-1]], [0]*9)


class Test_validate(tests.MuleTest):
    _dflt_nx = 4
    _dflt_ny = 3
    _dflt_nz = 5
    _dflt_x0 = 10.0
    _dflt_dx = 0.1
    _dflt_y0 = -60.0
    _dflt_dy = 0.2

    @staticmethod
    def _minimal_valid_lbc(nx=_dflt_nx, ny=_dflt_ny, nz=_dflt_nz,
                           x0=_dflt_x0, dx=_dflt_dx, y0=_dflt_y0, dy=_dflt_dy):
        # Construct a mock 'minimal' file that passes the validation tests.
        lbc = LBCFile()
        lbc.fixed_length_header.dataset_type = 5
        lbc.fixed_length_header.grid_staggering = 3
        lbc.integer_constants = LBC_IntegerConstants.empty()
        lbc.integer_constants.num_cols = nx
        lbc.integer_constants.num_rows = ny
        lbc.integer_constants.num_p_levels = nz
        lbc.real_constants = LBC_RealConstants.empty()
        lbc.real_constants.start_lon = x0
        lbc.real_constants.col_spacing = dx
        lbc.real_constants.start_lat = y0
        lbc.real_constants.row_spacing = dy
        lbc.level_dependent_constants = (
            LBC_LevelDependentConstants.empty(nz + 1))
        return lbc

    @staticmethod
    def _minimal_valid_field(nx=_dflt_nx, ny=_dflt_ny,
                             x0=_dflt_x0, dx=_dflt_dx,
                             y0=_dflt_y0, dy=_dflt_dy):
        # Construct a mock 'minimal' field that passes the validation tests.
        fld = Field3.empty()
        fld.lbrel = 3
        fld.lbrow = ny
        fld.bzy = y0 - dy
        fld.bdy = dy
        fld.lbnpt = nx
        fld.bzx = x0 - dx
        fld.bdx = dx
        return fld

    # Test the the above minimal example file does indeed validate
    def test_basic_ok(self):
        lbc = self._minimal_valid_lbc()
        lbc.validate()

    # Test that the accepted dataset types pass
    def test_dataset_types_ok(self):
        lbc = self._minimal_valid_lbc()
        lbc.fixed_length_header.dataset_type = 5
        lbc.validate()

    # Test that some incorrect dataset types fail
    def test_dataset_types_fail(self):
        lbc = self._minimal_valid_lbc()
        for dtype in (0, 1, 2, 4, -32768):
            lbc.fixed_length_header.dataset_type = dtype
            with self.assertRaisesRegexp(ValidateError,
                                         "Incorrect dataset_type"):
                lbc.validate()

    # Test that the accepted grid staggerings pass
    def test_grid_staggering_ok(self):
        lbc = self._minimal_valid_lbc()
        for stagger in (3, 6):
            lbc.fixed_length_header.grid_staggering = stagger
            lbc.validate()

    # Test that some incorrect grid staggerings fail
    def test_grid_staggering_fail(self):
        lbc = self._minimal_valid_lbc()
        for stagger in (2, 5, 0, -32768):
            lbc.fixed_length_header.grid_staggering = stagger
            with self.assertRaisesRegexp(ValidateError,
                                         "Unsupported grid_staggering"):
                lbc.validate()

    # Test that having no integer constants fails
    def test_missing_int_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.integer_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Integer constants not found"):
            lbc.validate()

    # Test that having no integer constants fails
    def test_missing_real_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.real_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Real constants not found"):
            lbc.validate()

    # Test that having no integer constants fails
    def test_missing_lev_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.level_dependent_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Level dependent constants not found"):
            lbc.validate()

    # Test that invalid shape integer constants fails
    def test_baddims_int_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.integer_constants = LBC_IntegerConstants.empty(5)
        with self.assertRaisesRegexp(ValidateError,
                                     "Incorrect number of integer constants"):
            lbc.validate()

    # Test that invalid shape real constants fails
    def test_baddims_real_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.real_constants = LBC_RealConstants.empty(7)
        with self.assertRaisesRegexp(ValidateError,
                                     "Incorrect number of real constants"):
            lbc.validate()

    # Test that invalid shape level dependent constants fails (first dim)
    def test_baddim_1_lev_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.level_dependent_constants = LBC_LevelDependentConstants.empty(7, 8)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped level dependent constants"):
            lbc.validate()

    # Test that invalid shape level dependent constants fails (second dim)
    def test_baddim_2_lev_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.level_dependent_constants = LBC_LevelDependentConstants.empty(6, 9)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped level dependent constants"):
            lbc.validate()

    # Test a variable resolution case
    def test_basic_varres_ok(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        lbc.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_1_row_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(4, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped row dependent constants"):
            lbc.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_2_row_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 3)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped row dependent constants"):
            lbc.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_1_col_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(5, 2))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped column dependent const"):
            lbc.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_2_col_consts_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 3))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped column dependent const"):
            lbc.validate()

    # Test that a file with a valid field passes
    def test_basic_field_ok(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        for header_release in (2, 3, -99):
            fld.lbrel = header_release
            lbc.fields = [fld]
            lbc.validate()

    # Test a field with an invalid header release fails
    def test_basic_field_release_fail(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.lbrel = 4
        lbc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field 0 has unrecognised release number 4"):
            lbc.validate()

    # Test a variable resolution field passes
    def test_basic_varres_field_ok(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = lbc.real_constants.real_mdi
        fld.bzy = lbc.real_constants.real_mdi
        fld.bdx = lbc.real_constants.real_mdi
        fld.bdy = lbc.real_constants.real_mdi
        lbc.fields = [fld]
        lbc.validate()

    # Test a variable resolution field with bad column count fails
    def test_basic_varres_field_cols_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.lbnpt = 6
        lbc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field 0 column count inconsistent"):
            lbc.validate()

    # Test a variable resolution field with bad row count fails
    def test_basic_varres_field_rows_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.lbrow = 5
        lbc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field 0 row count inconsistent"):
            lbc.validate()

    # Test a variable resolution field with non RMDI bzx fails
    def test_basic_varres_field_bzx_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = 4
        fld.bzy = lbc.real_constants.real_mdi
        fld.bdx = lbc.real_constants.real_mdi
        fld.bdy = lbc.real_constants.real_mdi
        lbc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field 0 start longitude \(bzx\) not RMDI"):
            lbc.validate()

    # Test a variable resolution field with non RMDI bzy fails
    def test_basic_varres_field_bzy_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = lbc.real_constants.real_mdi
        fld.bzy = 5
        fld.bdx = lbc.real_constants.real_mdi
        fld.bdy = lbc.real_constants.real_mdi
        lbc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field 0 start latitude \(bzy\) not RMDI"):
            lbc.validate()

    # Test a variable resolution field with non RMDI bdx fails
    def test_basic_varres_field_bdx_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = lbc.real_constants.real_mdi
        fld.bzy = lbc.real_constants.real_mdi
        fld.bdx = 0.2
        fld.bdy = lbc.real_constants.real_mdi
        lbc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field 0 longitude interval \(bdx\) not RMDI"):
            lbc.validate()

    # Test a variable resolution field with non RMDI bdy fails
    def test_basic_varres_field_bdy_fail(self):
        lbc = self._minimal_valid_lbc()
        lbc.row_dependent_constants = LBC_RowDependentConstants.empty(3, 2)
        lbc.column_dependent_constants = (
            LBC_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = lbc.real_constants.real_mdi
        fld.bzy = lbc.real_constants.real_mdi
        fld.bdx = lbc.real_constants.real_mdi
        fld.bdy = 0.1
        lbc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field 0 latitude interval \(bdy\) not RMDI"):
            lbc.validate()

    # Test lower boundary x value just within tolerance passes
    def test_basic_regular_min_x_ok(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.01 - 0.0001)
        fld.lbnpt -= 1
        lbc.fields = [fld]
        lbc.validate()

    # Test lower boundary x value just outside tolerance fails
    def test_basic_regular_min_x_fail(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.01 + 0.0001)
        fld.lbnpt -= 1
        lbc.fields = [fld]
        with self.assertRaisesRegexp(ValidateError, 'longitudes inconsistent'):
            lbc.validate()

    # Test upper boundary x value just within tolerance passes
    def test_basic_regular_max_x_ok(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bdx = fld.bdx*2.01
        fld.bzx = lbc.real_constants.start_lon - fld.bdx
        lbc.fields = [fld]
        lbc.validate()

    # Test upper boundary x value just outside tolerance fails
    def test_basic_regular_max_x_fail(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bdx = fld.bdx*2.02
        fld.bzx = lbc.real_constants.start_lon - fld.bdx
        lbc.fields = [fld]
        with self.assertRaisesRegexp(ValidateError, 'longitudes inconsistent'):
            lbc.validate()

    # Test lower boundary y value just within tolerance passes
    def test_basic_regular_min_y_ok(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.01 - 0.0001)
        fld.lbrow -= 1
        lbc.fields = [fld]
        lbc.validate()

    # Test lower boundary y value just outside tolerance fails
    def test_basic_regular_min_y_fail(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.01 + 0.0001)
        fld.lbrow -= 1
        lbc.fields = [fld]
        with self.assertRaisesRegexp(ValidateError, 'latitudes inconsistent'):
            lbc.validate()

    # Test upper boundary y value just within tolerance passes
    def test_basic_regular_max_y_ok(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bdy = fld.bdy*3.03
        fld.bzy = lbc.real_constants.start_lat - fld.bdy
        lbc.fields = [fld]
        lbc.validate()

    # Test upper boundary y value just outside tolerance fails
    def test_basic_regular_max_y_fail(self):
        lbc = self._minimal_valid_lbc()
        fld = self._minimal_valid_field()
        fld.bdy = fld.bdy*3.04
        fld.bzy = lbc.real_constants.start_lat - fld.bdy
        lbc.fields = [fld]
        with self.assertRaisesRegexp(ValidateError, 'latitudes inconsistent'):
            lbc.validate()


class Test_LBCOperators(tests.MuleTest):

    # Initialise the operators here
    to_mask_operator = LBCToMaskedArrayOperator()
    to_lbc_operator = MaskedArrayToLBCOperator()
    # The value of mdi can be anything that won't clash with the arrays
    # used below
    mdi = -1234.0

    def run_lbc_operators(self, nlevs, rim, halo_x, halo_y, data, valid):
        # Create a 5x5 field
        fld = Test_validate._minimal_valid_field(nx=5, ny=5)

        # Set the quantities which are needed for the operators to work
        fld.lbhem = 100 + nlevs
        fld.lbuser3 = 10000*rim + 100*halo_x + halo_y
        fld.bmdi = self.mdi

        # Create a provider from the data array and attach it to the field
        provider = ArrayDataProvider(data)
        fld.set_data_provider(provider)

        # Turn this into a masked array and compare it to the valid data
        masked = self.to_mask_operator(fld)
        self.assertArrayEqual(masked.get_data(), valid)

        # Now turn the masked array back into an lbc array and compare it
        # to the original data
        reformed = self.to_lbc_operator(masked)
        self.assertArrayEqual(reformed.get_data(), fld.get_data())

    def test_lbc_operator_simple_rim1(self):
        # A 5x5 grid, 1 level, no halos, rim width of 1
        data = np.arange(16).reshape(1, 16)
        mdi = self.mdi
        valid = [[
            [08.0, 09.0, 10.0, 11.0, 12.0],
            [13.0,  mdi,  mdi,  mdi, 05.0],
            [14.0,  mdi,  mdi,  mdi, 06.0],
            [15.0,  mdi,  mdi,  mdi, 07.0],
            [00.0, 01.0, 02.0, 03.0, 04.0]]]

        self.run_lbc_operators(1, 1, 0, 0, data, valid)

    def test_lbc_operator_simple_rim2(self):
        # A 5x5 grid, 1 level, no halos, rim width of 2
        data = np.arange(24).reshape(1, 24)
        mdi = self.mdi
        valid = [[
            [12.0, 13.0, 14.0, 15.0, 16.0],
            [17.0, 18.0, 19.0, 20.0, 21.0],
            [22.0, 23.0,  mdi, 10.0, 11.0],
            [00.0, 01.0, 02.0, 03.0, 04.0],
            [05.0, 06.0, 07.0, 08.0, 09.0]]]

        self.run_lbc_operators(1, 2, 0, 0, data, valid)

    def test_lbc_operator_simple_rim2_halo22(self):
        # A 5x5 grid, 1 level, halos of 2 and 2, rim width of 2
        data = np.arange(80).reshape(1, 80)
        mdi = self.mdi
        valid = [[
            [40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0],
            [49.0, 50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0],
            [58.0, 59.0, 60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0],
            [67.0, 68.0, 69.0, 70.0, 71.0, 72.0, 73.0, 74.0, 75.0],
            [76.0, 77.0, 78.0, 79.0,  mdi, 36.0, 37.0, 38.0, 39.0],
            [00.0, 01.0, 02.0, 03.0, 04.0, 05.0, 06.0, 07.0, 08.0],
            [09.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
            [18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0],
            [27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0]]]

        self.run_lbc_operators(1, 2, 2, 2, data, valid)

    def test_lbc_operator_simple_rim2_halo21(self):
        # A 5x5 grid, 1 level, halos of 2 and 1, rim width of 2
        data = np.arange(62).reshape(1, 62)
        mdi = self.mdi
        valid = [[
            [31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0],
            [38.0, 39.0, 40.0, 41.0, 42.0, 43.0, 44.0],
            [45.0, 46.0, 47.0, 48.0, 49.0, 50.0, 51.0],
            [52.0, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0],
            [59.0, 60.0, 61.0,  mdi, 28.0, 29.0, 30.0],
            [00.0, 01.0, 02.0, 03.0, 04.0, 05.0, 06.0],
            [07.0, 08.0, 09.0, 10.0, 11.0, 12.0, 13.0],
            [14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0],
            [21.0, 22.0, 23.0, 24.0, 25.0, 26.0, 27.0]]]

        self.run_lbc_operators(1, 2, 2, 1, data, valid)

    def test_lbc_operator_simple_rim2_halo12(self):
        # A 5x5 grid, 1 level, halos of 1 and 2, rim width of 2
        data = np.arange(62).reshape(1, 62)
        mdi = self.mdi
        valid = [[
            [31.0, 32.0, 33.0, 34.0, 35.0, 36.0, 37.0, 38.0, 39.0],
            [40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0],
            [49.0, 50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0],
            [58.0, 59.0, 60.0, 61.0,  mdi, 27.0, 28.0, 29.0, 30.0],
            [00.0, 01.0, 02.0, 03.0, 04.0, 05.0, 06.0, 07.0, 08.0],
            [09.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
            [18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0]]]

        self.run_lbc_operators(1, 2, 1, 2, data, valid)

    def test_lbc_operator_simple_rim2_halo22_lev3(self):
        # A 5x5 grid, 3 level, halos of 2 and 2, rim width of 2
        data = np.arange(240).reshape(3, 80)
        mdi = self.mdi

        # For the multi-level case this will be the valid output
        # on the bottom level:
        valid_lev1 = np.array([[
            [40.0, 41.0, 42.0, 43.0, 44.0, 45.0, 46.0, 47.0, 48.0],
            [49.0, 50.0, 51.0, 52.0, 53.0, 54.0, 55.0, 56.0, 57.0],
            [58.0, 59.0, 60.0, 61.0, 62.0, 63.0, 64.0, 65.0, 66.0],
            [67.0, 68.0, 69.0, 70.0, 71.0, 72.0, 73.0, 74.0, 75.0],
            [76.0, 77.0, 78.0, 79.0,  mdi, 36.0, 37.0, 38.0, 39.0],
            [00.0, 01.0, 02.0, 03.0, 04.0, 05.0, 06.0, 07.0, 08.0],
            [09.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
            [18.0, 19.0, 20.0, 21.0, 22.0, 23.0, 24.0, 25.0, 26.0],
            [27.0, 28.0, 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0]]])

        # The later levels will be the same shape (but update by adding the
        # total points and remember to set the middle point back to mdi)
        valid_lev2 = valid_lev1 + 80.0
        valid_lev2[0, 4, 4] = mdi
        valid_lev3 = valid_lev2 + 80.0
        valid_lev3[0, 4, 4] = mdi

        # Stack the above together to form the full output for the test
        valid = np.vstack((valid_lev1, valid_lev2, valid_lev3))

        self.run_lbc_operators(3, 2, 2, 2, data, valid)


if __name__ == '__main__':
    tests.main()
