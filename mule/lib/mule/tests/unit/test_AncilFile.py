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
Unit tests for :class:`mule.ancil.AncilFile`.

"""

from __future__ import (absolute_import, division, print_function)

import mule.tests as tests
from mule import AncilFile, Field3, _REAL_MDI
from mule.ancil import (Ancil_IntegerConstants, Ancil_RealConstants,
                        Ancil_LevelDependentConstants,
                        Ancil_RowDependentConstants,
                        Ancil_ColumnDependentConstants)
from mule.validators import ValidateError


class Test___init__(tests.MuleTest):
    """Check AncilFile __init__ method."""
    def test_new_ancilfile(self):
        anc = AncilFile()
        self.assertArrayEqual(anc.fixed_length_header.raw,
                              [None] + [-32768] * 256)

        self.assertIsNone(anc.integer_constants)
        self.assertIsNone(anc.real_constants)
        self.assertIsNone(anc.level_dependent_constants)
        self.assertIsNone(anc.row_dependent_constants)
        self.assertIsNone(anc.column_dependent_constants)
        self.assertEqual(anc.fields, [])


class Test_from_file(tests.MuleTest):
    """Checkout different creation routes for the same file."""
    def test_read_ancilfile(self):
        anc = AncilFile.from_file(
            tests.testdata_filepath("soil_params.anc"))
        self.assertEqual(type(anc), AncilFile)
        self.assertIsNotNone(anc.integer_constants)
        self.assertEqual(anc.integer_constants.shape, (15,))
        self.assertIsNotNone(anc.real_constants)
        self.assertEqual(anc.real_constants.shape, (6,))
        self.assertIsNotNone(anc.level_dependent_constants)
        self.assertEqual(anc.level_dependent_constants.shape, (1, 4))
        self.assertIsNone(anc.row_dependent_constants)
        self.assertIsNone(anc.column_dependent_constants)
        self.assertEqual(len(anc.fields), 11)
        self.assertEqual([fld.lbrel for fld in anc.fields[:-1]], [2]*10)
        self.assertEqual([fld.lbvc for fld in anc.fields[:-1]], [129]*10)


class Test_validate(tests.MuleTest):
    _dflt_nx = 4
    _dflt_ny = 3
    _dflt_nz = 5
    _dflt_x0 = 10.0
    _dflt_dx = 0.1
    _dflt_y0 = -60.0
    _dflt_dy = 0.2

    @staticmethod
    def _minimal_valid_anc(nx=_dflt_nx, ny=_dflt_ny, nz=_dflt_nz,
                           x0=_dflt_x0, dx=_dflt_dx, y0=_dflt_y0, dy=_dflt_dy):
        # Construct a mock 'minimal' file that passes the validation tests.
        anc = AncilFile()
        anc.fixed_length_header.dataset_type = 4
        anc.fixed_length_header.grid_staggering = 3
        anc.fixed_length_header.horiz_grid_type = 0
        anc.integer_constants = Ancil_IntegerConstants.empty()
        anc.integer_constants.num_cols = nx
        anc.integer_constants.num_rows = ny
        anc.integer_constants.num_levels = nz
        anc.real_constants = Ancil_RealConstants.empty()
        anc.real_constants.start_lon = x0
        anc.real_constants.col_spacing = dx
        anc.real_constants.start_lat = y0
        anc.real_constants.row_spacing = dy
        anc.level_dependent_constants = (
            Ancil_LevelDependentConstants.empty(nz))
        return anc

    @staticmethod
    def _minimal_valid_field(nx=_dflt_nx, ny=_dflt_ny,
                             x0=_dflt_x0, dx=_dflt_dx,
                             y0=_dflt_y0, dy=_dflt_dy):
        # Construct a mock 'minimal' field that passes the validation tests.
        fld = Field3.empty()
        fld.lbrel = 3
        fld.lbcode = 1
        fld.lbhem = 0
        fld.lbrow = ny
        fld.bzy = y0 - dy
        fld.bdy = dy
        fld.lbnpt = nx
        fld.bzx = x0 - dx
        fld.bdx = dx
        return fld

    # Test the the above minimal example file does indeed validate
    def test_basic_ok(self):
        anc = self._minimal_valid_anc()
        anc.validate()

    # Test that the accepted dataset types pass
    def test_dataset_types_ok(self):
        anc = self._minimal_valid_anc()
        anc.fixed_length_header.dataset_type = 4
        anc.validate()

    # Test that some incorrect dataset types fail
    def test_dataset_types_fail(self):
        anc = self._minimal_valid_anc()
        for dtype in (0, 1, 2, 5, -32768):
            anc.fixed_length_header.dataset_type = dtype
            with self.assertRaisesRegexp(ValidateError,
                                         "Incorrect dataset_type"):
                anc.validate()

    # Test that the accepted grid staggerings pass
    def test_grid_staggering_ok(self):
        anc = self._minimal_valid_anc()
        for stagger in (3, 6):
            anc.fixed_length_header.grid_staggering = stagger
            anc.validate()

    # Test that some incorrect grid staggerings fail
    def test_grid_staggering_fail(self):
        anc = self._minimal_valid_anc()
        for stagger in (2, 5, 0, -32768):
            anc.fixed_length_header.grid_staggering = stagger
            with self.assertRaisesRegexp(ValidateError,
                                         "Unsupported grid_staggering"):
                anc.validate()

    # Test that having no integer constants fails
    def test_missing_int_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.integer_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Integer constants not found"):
            anc.validate()

    # Test that having no integer constants fails
    def test_missing_real_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.real_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Real constants not found"):
            anc.validate()

    # Test that having no integer constants fails
    def test_missing_lev_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.level_dependent_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Level dependent constants not found"):
            anc.validate()

    # Test that invalid shape integer constants fails
    def test_baddims_int_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.integer_constants = Ancil_IntegerConstants.empty(5)
        with self.assertRaisesRegexp(ValidateError,
                                     "Incorrect number of integer constants"):
            anc.validate()

    # Test that invalid shape real constants fails
    def test_baddims_real_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.real_constants = Ancil_RealConstants.empty(7)
        with self.assertRaisesRegexp(ValidateError,
                                     "Incorrect number of real constants"):
            anc.validate()

    # Test that invalid shape level dependent constants fails (first dim)
    def test_baddim_1_lev_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.level_dependent_constants = (
            Ancil_LevelDependentConstants.empty(7, 8))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped level dependent constants"):
            anc.validate()

    # Test that invalid shape level dependent constants fails (second dim)
    def test_baddim_2_lev_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.level_dependent_constants = (
            Ancil_LevelDependentConstants.empty(6, 9))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped level dependent constants"):
            anc.validate()

    # Test a variable resolution case
    def test_basic_varres_ok(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        anc.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_1_row_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(4, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped row dependent constants"):
            anc.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_2_row_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 3))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped row dependent constants"):
            anc.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_1_col_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(5, 2))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped column dependent const"):
            anc.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_2_col_consts_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 3))
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped column dependent const"):
            anc.validate()

    # Test that a file with a valid field passes
    def test_basic_field_ok(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        for header_release in (2, 3, -99):
            fld.lbrel = header_release
            anc.fields = [fld]
            anc.validate()

    # Test a field with an invalid header release fails
    def test_basic_field_release_fail(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.lbrel = 4
        anc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field has unrecognised release number 4"):
            anc.validate()

    # Test a variable resolution field passes
    def test_basic_varres_field_ok(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = _REAL_MDI
        fld.bzy = _REAL_MDI
        fld.bdx = _REAL_MDI
        fld.bdy = _REAL_MDI
        anc.fields = [fld]
        anc.validate()

    # Test a variable resolution field with bad column count fails
    def test_basic_varres_field_cols_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.lbnpt = 6
        anc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field column count inconsistent"):
            anc.validate()

    # Test a variable resolution field with bad row count fails
    def test_basic_varres_field_rows_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.lbrow = 5
        anc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field row count inconsistent"):
            anc.validate()

    # Test a variable resolution field with non RMDI bzx fails
    def test_basic_varres_field_bzx_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = 4
        fld.bzy = _REAL_MDI
        fld.bdx = _REAL_MDI
        fld.bdy = _REAL_MDI
        anc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field start longitude \(bzx\) not RMDI"):
            anc.validate()

    # Test a variable resolution field with non RMDI bzy fails
    def test_basic_varres_field_bzy_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = _REAL_MDI
        fld.bzy = 5
        fld.bdx = _REAL_MDI
        fld.bdy = _REAL_MDI
        anc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field start latitude \(bzy\) not RMDI"):
            anc.validate()

    # Test a variable resolution field with non RMDI bdx fails
    def test_basic_varres_field_bdx_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = _REAL_MDI
        fld.bzy = _REAL_MDI
        fld.bdx = 0.2
        fld.bdy = _REAL_MDI
        anc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field longitude interval \(bdx\) not RMDI"):
            anc.validate()

    # Test a variable resolution field with non RMDI bdy fails
    def test_basic_varres_field_bdy_fail(self):
        anc = self._minimal_valid_anc()
        anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        fld = self._minimal_valid_field()
        fld.bzx = _REAL_MDI
        fld.bzy = _REAL_MDI
        fld.bdx = _REAL_MDI
        fld.bdy = 0.1
        anc.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field latitude interval \(bdy\) not RMDI"):
            anc.validate()

    # Test lower boundary x value just within tolerance passes
    def test_basic_regular_min_x_ok(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.01 - 0.0001)
        fld.lbnpt -= 1
        anc.fields = [fld]
        anc.validate()

    # Test lower boundary x value just outside tolerance fails
    def test_basic_regular_min_x_fail(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.01 + 0.0001)
        fld.lbnpt -= 1
        anc.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'longitudes inconsistent'):
            anc.validate()

    # Test upper boundary x value just within tolerance passes
    def test_basic_regular_max_x_ok(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bdx = fld.bdx*1.5
        fld.bzx = anc.real_constants.start_lon - fld.bdx
        anc.fields = [fld]
        anc.validate()

    # Test upper boundary x value just outside tolerance fails
    def test_basic_regular_max_x_fail(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bdx = fld.bdx*1.51
        fld.bzx = anc.real_constants.start_lon - fld.bdx
        anc.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'longitudes inconsistent'):
            anc.validate()

    # Test lower boundary y value just within tolerance passes
    def test_basic_regular_min_y_ok(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.01 - 0.0001)
        fld.lbrow -= 1
        anc.fields = [fld]
        anc.validate()

    # Test lower boundary y value just outside tolerance fails
    def test_basic_regular_min_y_fail(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.01 + 0.0001)
        fld.lbrow -= 1
        anc.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'latitudes inconsistent'):
            anc.validate()

    # Test upper boundary y value just within tolerance passes
    def test_basic_regular_max_y_ok(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bdy = fld.bdy*2.02
        fld.bzy = anc.real_constants.start_lat - fld.bdy
        anc.fields = [fld]
        anc.validate()

    # Test upper boundary y value just outside tolerance fails
    def test_basic_regular_max_y_fail(self):
        anc = self._minimal_valid_anc()
        fld = self._minimal_valid_field()
        fld.bdy = fld.bdy*2.03
        fld.bzy = anc.real_constants.start_lat - fld.bdy
        anc.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'latitudes inconsistent'):
            anc.validate()


if __name__ == '__main__':
    tests.main()
