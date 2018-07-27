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
Unit tests for :class:`mule.ff.FieldsFile`.

"""

from __future__ import (absolute_import, division, print_function)

import six
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
        with six.assertRaisesRegex(self,
                                   ValueError,
                                   '"dim1" has no valid default'):
            _ = FieldsFile.from_template(test_template)

    def test_unknown_element__fail(self):
        test_template = {"integer_constants": {'whatsthis': 3}}
        with six.assertRaisesRegex(
                self,
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

    def setUp(self, *args, **kwargs):
        # Call the original setup function
        super(Test_validate, self).setUp(*args, **kwargs)

        # Construct a mock 'minimal' file that passes the validation tests.
        self.ff = FieldsFile()
        self.ff.fixed_length_header.dataset_type = 3
        self.ff.fixed_length_header.grid_staggering = 3
        self.ff.fixed_length_header.horiz_grid_type = 0
        self.ff.integer_constants = FF_IntegerConstants.empty()
        self.ff.integer_constants.num_cols = self._dflt_nx
        self.ff.integer_constants.num_rows = self._dflt_ny
        self.ff.integer_constants.num_p_levels = self._dflt_nz
        self.ff.real_constants = FF_RealConstants.empty()
        self.ff.real_constants.start_lon = self._dflt_x0
        self.ff.real_constants.col_spacing = self._dflt_dx
        self.ff.real_constants.start_lat = self._dflt_y0
        self.ff.real_constants.row_spacing = self._dflt_dy
        self.ff.level_dependent_constants = (
            FF_LevelDependentConstants.empty(self._dflt_nz + 1))

        # Construct a mock 'minimal' field that passes the validation tests.
        self.fld = Field3.empty()
        self.fld.lbrel = 3
        self.fld.lbcode = 1
        self.fld.lbhem = 0
        self.fld.lbrow = self._dflt_ny
        self.fld.bzy = self._dflt_y0 - self._dflt_dy
        self.fld.bdy = self._dflt_dy
        self.fld.lbnpt = self._dflt_nx
        self.fld.bzx = self._dflt_x0 - self._dflt_dx
        self.fld.bdx = self._dflt_dx

    # Test the the above minimal example file does indeed validate
    def test_basic_ok(self):
        self.ff.validate()

    # Test that the accepted dataset type passes
    def test_dataset_types_ok(self):
        self.ff.fixed_length_header.dataset_type = 3
        self.ff.validate()

    # Test that some incorrect dataset types fail
    def test_dataset_types_fail(self):
        for dtype in (0, 1, 2, 4, 5, 6, -32768):
            self.ff.fixed_length_header.dataset_type = dtype
            with six.assertRaisesRegex(self,
                                       ValidateError,
                                       "Incorrect dataset_type"):
                self.ff.validate()

    # Test that the accepted grid staggerings pass
    def test_grid_staggering_ok(self):
        for stagger in (3, 6):
            self.ff.fixed_length_header.grid_staggering = stagger
            self.ff.validate()

    # Test that some incorrect grid staggerings fail
    def test_grid_staggering_fail(self):
        for stagger in (2, 5, 0, -32768):
            self.ff.fixed_length_header.grid_staggering = stagger
            with six.assertRaisesRegex(self,
                                       ValidateError,
                                       "Unsupported grid_staggering"):
                self.ff.validate()

    # Test that having no integer constants fails
    def test_missing_int_consts_fail(self):
        self.ff.integer_constants = None
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Integer constants not found"):
            self.ff.validate()

    # Test that having no integer constants fails
    def test_missing_real_consts_fail(self):
        self.ff.real_constants = None
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Real constants not found"):
            self.ff.validate()

    # Test that having no integer constants fails
    def test_missing_lev_consts_fail(self):
        self.ff.level_dependent_constants = None
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Level dependent constants not found"):
            self.ff.validate()

    # Test that invalid shape integer constants fails
    def test_baddims_int_consts_fail(self):
        self.ff.integer_constants = FF_IntegerConstants.empty(5)
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Incorrect number of integer constants"):
            self.ff.validate()

    # Test that invalid shape real constants fails
    def test_baddims_real_consts_fail(self):
        self.ff.real_constants = FF_RealConstants.empty(7)
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Incorrect number of real constants"):
            self.ff.validate()

    # Test that invalid shape level dependent constants fails (first dim)
    def test_baddim_1_lev_consts_fail(self):
        self.ff.level_dependent_constants = (
            FF_LevelDependentConstants.empty(7, 8))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped level dependent constants"):
            self.ff.validate()

    # Test that invalid shape level dependent constants fails (second dim)
    def test_baddim_2_lev_consts_fail(self):
        self.ff.level_dependent_constants = (
            FF_LevelDependentConstants.empty(6, 9))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped level dependent constants"):
            self.ff.validate()

    # Test a variable resolution case
    def test_basic_varres_ok(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.ff.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_1_row_consts_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(4, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped row dependent constants"):
            self.ff.validate()

    # Test that an invalid shape row dependent constants fails (first dim)
    def test_baddim_2_row_consts_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 3)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped row dependent constants"):
            self.ff.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_1_col_consts_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(5, 2))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped column dependent const"):
            self.ff.validate()

    # Test that an invalid shape column dependent constants fails (first dim)
    def test_baddim_2_col_consts_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 3))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped column dependent const"):
            self.ff.validate()

    # Test that a file with a valid field passes
    def test_basic_field_ok(self):
        for header_release in (2, 3, -99):
            self.fld.lbrel = header_release
            self.ff.fields = [self.fld]
            self.ff.validate()

    # Test a field with an invalid header release fails
    def test_basic_field_release_fail(self):
        self.fld.lbrel = 4
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field has unrecognised release number 4"):
            self.ff.validate()

    # Test a land/sea packed field
    def test_basic_field_landsea_ok(self):
        self.fld.lbpack = 120
        self.fld.lbrow = 0
        self.fld.lbnpt = 0
        self.ff.fields = [self.fld]
        self.ff.validate()

    # Test a land/sea packed field with bad row setting fails
    def test_basic_field_landsea_row_fail(self):
        self.fld.lbpack = 120
        self.fld.lbnpt = 0
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field rows not set to zero"):
            self.ff.validate()

    # Test a land/sea packed field with bad column setting fails
    def test_basic_field_landsea_column_fail(self):
        self.fld.lbpack = 120
        self.fld.lbrow = 0
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field columns not set to zero"):
            self.ff.validate()

    # Test a variable resolution field passes
    def test_basic_varres_field_ok(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.fld.bzx = self.ff.real_constants.real_mdi
        self.fld.bzy = self.ff.real_constants.real_mdi
        self.fld.bdx = self.ff.real_constants.real_mdi
        self.fld.bdy = self.ff.real_constants.real_mdi
        self.ff.fields = [self.fld]
        self.ff.validate()

    # Test a variable resolution field with bad column count fails
    def test_basic_varres_field_cols_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.fld.lbnpt = 6
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field column count inconsistent"):
            self.ff.validate()

    # Test a variable resolution field with bad row count fails
    def test_basic_varres_field_rows_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.fld.lbrow = 5
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field row count inconsistent"):
            self.ff.validate()

    # Test a variable resolution field with non RMDI bzx fails
    def test_basic_varres_field_bzx_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.fld.bzx = 4
        self.fld.bzy = self.ff.real_constants.real_mdi
        self.fld.bdx = self.ff.real_constants.real_mdi
        self.fld.bdy = self.ff.real_constants.real_mdi
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field start longitude \(bzx\) not RMDI"):
            self.ff.validate()

    # Test a variable resolution field with non RMDI bzy fails
    def test_basic_varres_field_bzy_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.fld.bzx = self.ff.real_constants.real_mdi
        self.fld.bzy = 5
        self.fld.bdx = self.ff.real_constants.real_mdi
        self.fld.bdy = self.ff.real_constants.real_mdi
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field start latitude \(bzy\) not RMDI"):
            self.ff.validate()

    # Test a variable resolution field with non RMDI bdx fails
    def test_basic_varres_field_bdx_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.fld.bzx = self.ff.real_constants.real_mdi
        self.fld.bzy = self.ff.real_constants.real_mdi
        self.fld.bdx = 0.2
        self.fld.bdy = self.ff.real_constants.real_mdi
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field longitude interval \(bdx\) not RMDI"):
            self.ff.validate()

    # Test a variable resolution field with non RMDI bdy fails
    def test_basic_varres_field_bdy_fail(self):
        self.ff.row_dependent_constants = FF_RowDependentConstants.empty(3, 2)
        self.ff.column_dependent_constants = (
            FF_ColumnDependentConstants.empty(4, 2))
        self.fld.bzx = self.ff.real_constants.real_mdi
        self.fld.bzy = self.ff.real_constants.real_mdi
        self.fld.bdx = self.ff.real_constants.real_mdi
        self.fld.bdy = 0.1
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field latitude interval \(bdy\) not RMDI"):
            self.ff.validate()

    # Test lower boundary x value just within tolerance passes
    def test_basic_regular_min_x_ok(self):
        self.fld.bzx += self.fld.bdx * (1.01 - 0.0001)
        self.fld.lbnpt -= 1
        self.ff.fields = [self.fld]
        self.ff.validate()

    # Test lower boundary x value just outside tolerance fails
    def test_basic_regular_min_x_fail(self):
        self.fld.bzx += self.fld.bdx * (1.01 + 0.0001)
        self.fld.lbnpt -= 1
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'longitudes inconsistent'):
            self.ff.validate()

    # Test upper boundary x value just within tolerance passes
    def test_basic_regular_max_x_ok(self):
        self.fld.bdx = self.fld.bdx*1.5
        self.fld.bzx = self.ff.real_constants.start_lon - self.fld.bdx
        self.ff.fields = [self.fld]
        self.ff.validate()

    # Test upper boundary x value just outside tolerance fails
    def test_basic_regular_max_x_fail(self):
        self.fld.bdx = self.fld.bdx*1.51
        self.fld.bzx = self.ff.real_constants.start_lon - self.fld.bdx
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'longitudes inconsistent'):
            self.ff.validate()

    # Test lower boundary y value just within tolerance passes
    def test_basic_regular_min_y_ok(self):
        self.fld.bzy += self.fld.bdy * (1.01 - 0.0001)
        self.fld.lbrow -= 1
        self.ff.fields = [self.fld]
        self.ff.validate()

    # Test lower boundary y value just outside tolerance fails
    def test_basic_regular_min_y_fail(self):
        self.fld.bzy += self.fld.bdy * (1.01 + 0.0001)
        self.fld.lbrow -= 1
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'latitudes inconsistent'):
            self.ff.validate()

    # Test upper boundary y value just within tolerance passes
    def test_basic_regular_max_y_ok(self):
        self.fld.bdy = self.fld.bdy*2.02
        self.fld.bzy = self.ff.real_constants.start_lat - self.fld.bdy
        self.ff.fields = [self.fld]
        self.ff.validate()

    # Test upper boundary y value just outside tolerance fails
    def test_basic_regular_max_y_fail(self):
        self.fld.bdy = self.fld.bdy*2.03
        self.fld.bzy = self.ff.real_constants.start_lat - self.fld.bdy
        self.ff.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'latitudes inconsistent'):
            self.ff.validate()


if __name__ == '__main__':
    tests.main()
