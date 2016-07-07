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
Unit tests for :class:`mule.ff.FieldsFile`.

"""

from __future__ import (absolute_import, division, print_function)

import mule.tests as tests
from mule.tests import check_common_n48_testdata, COMMON_N48_TESTDATA_PATH

from mule import FieldsFile, Field3
from mule.ff import (FF_IntegerConstants, FF_RealConstants,
                     FF_LevelDependentConstants, FF_RowDependentConstants,
                     FF_ColumnDependentConstants)
from mule.validators import ValidateError


class Test___init__(tests.MuleTest):
    """Check FieldsFile __init__ method."""
    def test_new_fieldsfile(self):
        ffv = FieldsFile()
        self.assertArrayEqual(ffv.fixed_length_header.raw,
                              [None] + [-32768] * 256)

        self.assertIsNone(ffv.integer_constants)
        self.assertIsNone(ffv.real_constants)
        self.assertIsNone(ffv.level_dependent_constants)
        self.assertIsNone(ffv.row_dependent_constants)
        self.assertIsNone(ffv.column_dependent_constants)
        self.assertEqual(ffv.fields, [])


class Test_from_file(tests.MuleTest):
    """Checkout different creation routes for the same file."""
    def test_read_fieldsfile(self):
        ffv = FieldsFile.from_file(COMMON_N48_TESTDATA_PATH)
        self.assertEqual(type(ffv), FieldsFile)
        check_common_n48_testdata(self, ffv)


class Test_from_template(tests.MuleTest):
    def test_fieldsfile_minimal_create(self):
        ffv = FieldsFile.from_template({'integer_constants': {},
                                        'real_constants': {}})
        self.assertEqual(ffv.integer_constants.shape, (46,))
        self.assertEqual(ffv.real_constants.shape, (38,))

    def test_minimal_component(self):
        test_template = {"integer_constants": {}}
        ffv = FieldsFile.from_template(test_template)
        self.assertEqual(ffv.integer_constants.shape, (46,))
        self.assertIsNone(ffv.real_constants)

    def test_component_sizing(self):
        test_template = {"real_constants": {'dims': (9,)}}
        ffv = FieldsFile.from_template(test_template)
        self.assertEqual(ffv.real_constants.shape, (9,))
        self.assertIsNone(ffv.integer_constants)

    def test_component_withdims(self):
        test_template = {"row_dependent_constants": {'dims': (13,)}}
        ffv = FieldsFile.from_template(test_template)
        self.assertEqual(ffv.row_dependent_constants.shape, (13, 2))

    def test_component_nodims__error(self):
        test_template = {"row_dependent_constants": {}}
        with self.assertRaisesRegexp(ValueError,
                                     '"dim1" has no valid default'):
            _ = FieldsFile.from_template(test_template)

    def test_unknown_element__fail(self):
        test_template = {"integer_constants": {'whatsthis': 3}}
        with self.assertRaisesRegexp(
                ValueError,
                '"integer_constants".*no element.*"whatsthis"'):
            _ = FieldsFile.from_template(test_template)

    def test_create_from_template(self):
        test_template = {
            "fixed_length_header": {
                "data_set_format_version": 20,
                "sub_model": 1,
                "vert_coord_type": 5,
                "horiz_grid_type": 0,
                "dataset_type": 3,
                "run_identifier": 0,
                "calendar": 1,
                "grid_staggering": 3,
                "model_version": 802,
                },
            "integer_constants": {
                "num_cols": 96,
                "num_rows": 73,
                "num_p_levels": 70,
                "num_wet_levels": 70,
                "num_soil_levels": 4,
                "num_tracer_levels": 70,
                "num_boundary_levels": 50,
                "height_algorithm": 2,
                "first_constant_rho": 50,
                "num_land_points": 2381,
                "num_soil_hydr_levels": 4,
                },
            "real_constants": {
                "col_spacing": 3.75,
                "row_spacing": 2.5,
                "start_lat": -90.0,
                "start_lon": 0.0,
                "north_pole_lat": 90.0,
                "north_pole_lon": 0.0,
                "top_theta_height": 80000.0,
                },
            "level_dependent_constants": {
                'dims': (71,),  # this one absolutely *is* needed
                },
            }
        ff_new = FieldsFile.from_template(test_template)
        with self.temp_filename() as temp_path:
            ff_new.to_file(temp_path)
            ffv_reload = FieldsFile.from_file(temp_path)
        self.assertIsNone(ffv_reload.row_dependent_constants)
        self.assertIsNone(ffv_reload.column_dependent_constants)
        self.assertEqual(ffv_reload.level_dependent_constants.raw.shape,
                         (71, 9))


class Test_validate(tests.MuleTest):
    _dflt_nx = 4
    _dflt_ny = 3
    _dflt_nz = 5
    _dflt_x0 = 10.0
    _dflt_dx = 0.1
    _dflt_y0 = -60.0
    _dflt_dy = 0.2

    @staticmethod
    def _minimal_valid_ff(nx=_dflt_nx, ny=_dflt_ny, nz=_dflt_nz,
                          x0=_dflt_x0, dx=_dflt_dx, y0=_dflt_y0, dy=_dflt_dy):
        # Construct a mock 'minimal' file that passes the validation tests.
        ff = FieldsFile()
        ff.fixed_length_header.dataset_type = 3
        ff.fixed_length_header.grid_staggering = 3
        ff.fixed_length_header.horiz_grid_type = 0
        ff.integer_constants = FF_IntegerConstants.empty()
        ff.integer_constants.num_cols = nx
        ff.integer_constants.num_rows = ny
        ff.integer_constants.num_p_levels = nz
        ff.real_constants = FF_RealConstants.empty()
        ff.real_constants.start_lon = x0
        ff.real_constants.col_spacing = dx
        ff.real_constants.start_lat = y0
        ff.real_constants.row_spacing = dy
        ff.level_dependent_constants = FF_LevelDependentConstants.empty(nz + 1)
        return ff

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
        ff = self._minimal_valid_ff()
        ff.validate()

    # Test that the accepted dataset types pass
    def test_dataset_types_ok(self):
        ff = self._minimal_valid_ff()
        for dtype in (1, 2, 3):
            ff.fixed_length_header.dataset_type = dtype
            ff.validate()

    # Test that some incorrect dataset types fail
    def test_dataset_types_fail(self):
        ff = self._minimal_valid_ff()
        for dtype in (0, 4, 5, 6, -32768):
            ff.fixed_length_header.dataset_type = dtype
            with self.assertRaisesRegexp(ValidateError,
                                         "Incorrect dataset_type"):
                ff.validate()

    # Test that the accepted grid staggerings pass
    def test_grid_staggering_ok(self):
        ff = self._minimal_valid_ff()
        for stagger in (3, 6):
            ff.fixed_length_header.grid_staggering = stagger
            ff.validate()

    # Test that some incorrect grid staggerings fail
    def test_grid_staggering_fail(self):
        ff = self._minimal_valid_ff()
        for stagger in (2, 5, 0, -32768):
            ff.fixed_length_header.grid_staggering = stagger
            with self.assertRaisesRegexp(ValidateError,
                                         "Unsupported grid_staggering"):
                ff.validate()

    # Test that having no integer constants fails
    def test_missing_int_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.integer_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Integer constants not found"):
            ff.validate()

    # Test that having no integer constants fails
    def test_missing_real_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.real_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Real constants not found"):
            ff.validate()

    # Test that having no integer constants fails
    def test_missing_lev_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.level_dependent_constants = None
        with self.assertRaisesRegexp(ValidateError,
                                     "Level dependent constants not found"):
            ff.validate()

    # Test that invalid shape integer constants fails
    def test_baddims_int_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.integer_constants = FF_IntegerConstants.empty(5)
        with self.assertRaisesRegexp(ValidateError,
                                     "Incorrect number of integer constants"):
            ff.validate()

    # Test that invalid shape real constants fails
    def test_baddims_real_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.real_constants = FF_RealConstants.empty(7)
        with self.assertRaisesRegexp(ValidateError,
                                     "Incorrect number of real constants"):
            ff.validate()

    # Test that invalid shape level dependent constants fails (first dim)
    def test_baddim_1_lev_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.level_dependent_constants = FF_LevelDependentConstants.empty(7, 8)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped level dependent constants"):
            ff.validate()

    # Test that invalid shape level dependent constants fails (second dim)
    def test_baddim_2_lev_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.level_dependent_constants = FF_LevelDependentConstants.empty(6, 9)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped level dependent constants"):
            ff.validate()

    # Test a variable resolution case
    def test_basic_varres_ok(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        ff.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_1_row_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(4, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped row dependent constants"):
            ff.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_2_row_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 3)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped row dependent constants"):
            ff.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_1_col_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(5, 2)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped column dependent const"):
            ff.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_2_col_consts_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 3)
        with self.assertRaisesRegexp(
                ValidateError, "Incorrectly shaped column dependent const"):
            ff.validate()

    # Test that a file with a valid field passes
    def test_basic_field_ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        for header_release in (2, 3, -99):
            fld.lbrel = header_release
            ff.fields = [fld]
            ff.validate()

    # Test a field with an invalid header release fails
    def test_basic_field_release_fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.lbrel = 4
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field has unrecognised release number 4"):
            ff.validate()

    # Test a land/sea packed field
    def test_basic_field_landsea_ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.lbpack = 120
        fld.lbrow = 0
        fld.lbnpt = 0
        ff.fields = [fld]
        ff.validate()

    # Test a land/sea packed field with bad row setting fails
    def test_basic_field_landsea_row_fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.lbpack = 120
        fld.lbnpt = 0
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field rows not set to zero"):
            ff.validate()

    # Test a land/sea packed field with bad column setting fails
    def test_basic_field_landsea_column_fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.lbpack = 120
        fld.lbrow = 0
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field columns not set to zero"):
            ff.validate()

    # Test a variable resolution field passes
    def test_basic_varres_field_ok(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        fld = self._minimal_valid_field()
        fld.bzx = ff.real_constants.real_mdi
        fld.bzy = ff.real_constants.real_mdi
        fld.bdx = ff.real_constants.real_mdi
        fld.bdy = ff.real_constants.real_mdi
        ff.fields = [fld]
        ff.validate()

    # Test a variable resolution field with bad column count fails
    def test_basic_varres_field_cols_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        fld = self._minimal_valid_field()
        fld.lbnpt = 6
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field column count inconsistent"):
            ff.validate()

    # Test a variable resolution field with bad row count fails
    def test_basic_varres_field_rows_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        fld = self._minimal_valid_field()
        fld.lbrow = 5
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field row count inconsistent"):
            ff.validate()

    # Test a variable resolution field with non RMDI bzx fails
    def test_basic_varres_field_bzx_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        fld = self._minimal_valid_field()
        fld.bzx = 4
        fld.bzy = ff.real_constants.real_mdi
        fld.bdx = ff.real_constants.real_mdi
        fld.bdy = ff.real_constants.real_mdi
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field start longitude \(bzx\) not RMDI"):
            ff.validate()

    # Test a variable resolution field with non RMDI bzy fails
    def test_basic_varres_field_bzy_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        fld = self._minimal_valid_field()
        fld.bzx = ff.real_constants.real_mdi
        fld.bzy = 5
        fld.bdx = ff.real_constants.real_mdi
        fld.bdy = ff.real_constants.real_mdi
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field start latitude \(bzy\) not RMDI"):
            ff.validate()

    # Test a variable resolution field with non RMDI bdx fails
    def test_basic_varres_field_bdx_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        fld = self._minimal_valid_field()
        fld.bzx = ff.real_constants.real_mdi
        fld.bzy = ff.real_constants.real_mdi
        fld.bdx = 0.2
        fld.bdy = ff.real_constants.real_mdi
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field longitude interval \(bdx\) not RMDI"):
            ff.validate()

    # Test a variable resolution field with non RMDI bdy fails
    def test_basic_varres_field_bdy_fail(self):
        ff = self._minimal_valid_ff()
        ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        ff.column_dependent_constants = FF_ColumnDependentConstants.empty(4, 2)
        fld = self._minimal_valid_field()
        fld.bzx = ff.real_constants.real_mdi
        fld.bzy = ff.real_constants.real_mdi
        fld.bdx = ff.real_constants.real_mdi
        fld.bdy = 0.1
        ff.fields = [fld]
        with self.assertRaisesRegexp(
                ValidateError, "Field latitude interval \(bdy\) not RMDI"):
            ff.validate()

    # Test lower boundary x value just within tolerance passes
    def test_basic_regular_min_x_ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.01 - 0.0001)
        fld.lbnpt -= 1
        ff.fields = [fld]
        ff.validate()

    # Test lower boundary x value just outside tolerance fails
    def test_basic_regular_min_x_fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.01 + 0.0001)
        fld.lbnpt -= 1
        ff.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'longitudes inconsistent'):
            ff.validate()

    # Test upper boundary x value just within tolerance passes
    def test_basic_regular_max_x_ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bdx = fld.bdx*1.5
        fld.bzx = ff.real_constants.start_lon - fld.bdx
        ff.fields = [fld]
        ff.validate()

    # Test upper boundary x value just outside tolerance fails
    def test_basic_regular_max_x_fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bdx = fld.bdx*1.51
        fld.bzx = ff.real_constants.start_lon - fld.bdx
        ff.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'longitudes inconsistent'):
            ff.validate()

    # Test lower boundary y value just within tolerance passes
    def test_basic_regular_min_y_ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.01 - 0.0001)
        fld.lbrow -= 1
        ff.fields = [fld]
        ff.validate()

    # Test lower boundary y value just outside tolerance fails
    def test_basic_regular_min_y_fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.01 + 0.0001)
        fld.lbrow -= 1
        ff.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'latitudes inconsistent'):
            ff.validate()

    # Test upper boundary y value just within tolerance passes
    def test_basic_regular_max_y_ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bdy = fld.bdy*2.02
        fld.bzy = ff.real_constants.start_lat - fld.bdy
        ff.fields = [fld]
        ff.validate()

    # Test upper boundary y value just outside tolerance fails
    def test_basic_regular_max_y_fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bdy = fld.bdy*2.03
        fld.bzy = ff.real_constants.start_lat - fld.bdy
        ff.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'latitudes inconsistent'):
            ff.validate()


if __name__ == '__main__':
    tests.main()
