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
Unit tests for :class:`mule.ancil.AncilFile`.

"""

from __future__ import (absolute_import, division, print_function)

import six
import warnings

import mule.tests as tests
from mule import AncilFile, Field3, _REAL_MDI
from mule.ancil import (Ancil_IntegerConstants, Ancil_RealConstants,
                        Ancil_RowDependentConstants,
                        Ancil_ColumnDependentConstants)
from mule.ff import FF_LevelDependentConstants
from mule.validators import ValidateError

warnings.filterwarnings("ignore", r".*No STASHmaster file loaded.*")


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
        with warnings.catch_warnings():
            msg_exp = r".*Ancillary files do not define.*"
            warnings.filterwarnings("ignore", msg_exp)
            anc = AncilFile.from_file(
                tests.testdata_filepath("soil_params.anc"))
            self.assertEqual(type(anc), AncilFile)
            self.assertIsNotNone(anc.integer_constants)
            self.assertEqual(anc.integer_constants.shape, (15,))
            self.assertIsNotNone(anc.real_constants)
            self.assertEqual(anc.real_constants.shape, (6,))
            self.assertIsNone(anc.level_dependent_constants)
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

    def setUp(self, *args, **kwargs):
        # Call the original setup function
        super(Test_validate, self).setUp(*args, **kwargs)

        # Construct a mock 'minimal' file that passes the validation tests.
        self.anc = AncilFile()
        self.anc.fixed_length_header.dataset_type = 4
        self.anc.fixed_length_header.grid_staggering = 3
        self.anc.fixed_length_header.horiz_grid_type = 0
        self.anc.integer_constants = Ancil_IntegerConstants.empty()
        self.anc.integer_constants.num_cols = self._dflt_nx
        self.anc.integer_constants.num_rows = self._dflt_ny
        self.anc.integer_constants.num_levels = self._dflt_nz
        self.anc.real_constants = Ancil_RealConstants.empty()
        self.anc.real_constants.start_lon = self._dflt_x0
        self.anc.real_constants.col_spacing = self._dflt_dx
        self.anc.real_constants.start_lat = self._dflt_y0
        self.anc.real_constants.row_spacing = self._dflt_dy

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
        self.anc.validate()

    # Test that the accepted dataset types pass
    def test_dataset_types_ok(self):
        self.anc.fixed_length_header.dataset_type = 4
        self.anc.validate()

    # Test that some incorrect dataset types fail
    def test_dataset_types_fail(self):
        for dtype in (0, 1, 2, 5, -32768):
            self.anc.fixed_length_header.dataset_type = dtype
            with six.assertRaisesRegex(self,
                                       ValidateError,
                                       "Incorrect dataset_type"):
                self.anc.validate()

    # Test that the accepted grid staggerings pass
    def test_grid_staggering_ok(self):
        for stagger in (3, 6):
            self.anc.fixed_length_header.grid_staggering = stagger
            self.anc.validate()

    # Test that some incorrect grid staggerings fail
    def test_grid_staggering_fail(self):
        for stagger in (5, 0, -32768):
            self.anc.fixed_length_header.grid_staggering = stagger
            with six.assertRaisesRegex(self,
                                       ValidateError,
                                       "Unsupported grid_staggering"):
                self.anc.validate()

    # Test that grid staggering of 2 passes for depths only
    def test_grid_staggering_depth(self):
        self.anc.fixed_length_header.grid_staggering = 2
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Unsupported grid_staggering"):
            self.anc.validate()
        self.anc.fixed_length_header.vert_coord_type = 4
        self.assertIsNone(self.anc.validate())

    # Test that having no integer constants fails
    def test_missing_int_consts_fail(self):
        self.anc.integer_constants = None
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Integer constants not found"):
            self.anc.validate()

    # Test that having no integer constants fails
    def test_missing_real_consts_fail(self):
        self.anc.real_constants = None
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Real constants not found"):
            self.anc.validate()

    # Test that having level dependent constants fails
    def test_having_lev_consts_fail(self):
        self.anc.level_dependent_constants = (
            FF_LevelDependentConstants.empty(2))
        with six.assertRaisesRegex(
                self,
                ValidateError,
                "Ancillary file contains header components other than"):
            self.anc.validate()

    # Test that invalid shape integer constants fails
    def test_baddims_int_consts_fail(self):
        self.anc.integer_constants = Ancil_IntegerConstants.empty(5)
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Incorrect number of integer constants"):
            self.anc.validate()

    # Test that invalid shape real constants fails
    def test_baddims_real_consts_fail(self):
        self.anc.real_constants = Ancil_RealConstants.empty(7)
        with six.assertRaisesRegex(self,
                                   ValidateError,
                                   "Incorrect number of real constants"):
            self.anc.validate()

    # Test a variable resolution case
    def test_basic_varres_ok(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.anc.validate()

    # Test that an invalid shape row dependent constants fails (length)
    def test_baddim_1_row_consts_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(4))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped row dependent constants"):
            self.anc.validate()

    # Test that an invalid shape row dependent constants fails (extra dim)
    def test_baddim_2_row_consts_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3, 2))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped row dependent constants"):
            self.anc.validate()

    # Test that an invalid shape column dependent constants fails (length)
    def test_baddim_1_col_consts_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(5))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped column dependent const"):
            self.anc.validate()

    # Test that an invalid shape column dependent constants fails (extra dim)
    def test_baddim_2_col_consts_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4, 2))
        with six.assertRaisesRegex(
            self, ValidateError,
                "Incorrectly shaped column dependent const"):
            self.anc.validate()

    # Test that a file with a valid field passes
    def test_basic_field_ok(self):
        for header_release in (2, 3, -99):
            self.fld.lbrel = header_release
            self.anc.fields = [self.fld]
            self.anc.validate()

    # Test a field with an invalid header release fails
    def test_basic_field_release_fail(self):
        self.fld.lbrel = 4
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field has unrecognised release number 4"):
            self.anc.validate()

    # Test a variable resolution field passes
    def test_basic_varres_field_ok(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.fld.bzx = _REAL_MDI
        self.fld.bzy = _REAL_MDI
        self.fld.bdx = _REAL_MDI
        self.fld.bdy = _REAL_MDI
        self.anc.fields = [self.fld]
        self.anc.validate()

    # Test a variable resolution field with bad column count fails
    def test_basic_varres_field_cols_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.fld.lbnpt = 6
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field column count inconsistent"):
            self.anc.validate()

    # Test a variable resolution field with bad row count fails
    def test_basic_varres_field_rows_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.fld.lbrow = 5
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field row count inconsistent"):
            self.anc.validate()

    # Test a variable resolution field with non RMDI bzx fails
    def test_basic_varres_field_bzx_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.fld.bzx = 4
        self.fld.bzy = _REAL_MDI
        self.fld.bdx = _REAL_MDI
        self.fld.bdy = _REAL_MDI
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field start longitude \(bzx\) not RMDI"):
            self.anc.validate()

    # Test a variable resolution field with non RMDI bzy fails
    def test_basic_varres_field_bzy_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.fld.bzx = _REAL_MDI
        self.fld.bzy = 5
        self.fld.bdx = _REAL_MDI
        self.fld.bdy = _REAL_MDI
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field start latitude \(bzy\) not RMDI"):
            self.anc.validate()

    # Test a variable resolution field with non RMDI bdx fails
    def test_basic_varres_field_bdx_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.fld.bzx = _REAL_MDI
        self.fld.bzy = _REAL_MDI
        self.fld.bdx = 0.2
        self.fld.bdy = _REAL_MDI
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field longitude interval \(bdx\) not RMDI"):
            self.anc.validate()

    # Test a variable resolution field with non RMDI bdy fails
    def test_basic_varres_field_bdy_fail(self):
        self.anc.row_dependent_constants = (
            Ancil_RowDependentConstants.empty(3))
        self.anc.column_dependent_constants = (
            Ancil_ColumnDependentConstants.empty(4))
        self.fld.bzx = _REAL_MDI
        self.fld.bzy = _REAL_MDI
        self.fld.bdx = _REAL_MDI
        self.fld.bdy = 0.1
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(
            self, ValidateError,
                "Field latitude interval \(bdy\) not RMDI"):
            self.anc.validate()

    # Test lower boundary x value just within tolerance passes
    def test_basic_regular_min_x_ok(self):
        self.fld.bzx += self.fld.bdx * (1.01 - 0.0001)
        self.fld.lbnpt -= 1
        self.anc.fields = [self.fld]
        self.anc.validate()

    # Test lower boundary x value just outside tolerance fails
    def test_basic_regular_min_x_fail(self):
        self.fld.bzx += self.fld.bdx * (1.01 + 0.0001)
        self.fld.lbnpt -= 1
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'longitudes inconsistent'):
            self.anc.validate()

    # Test upper boundary x value just within tolerance passes
    def test_basic_regular_max_x_ok(self):
        self.fld.bdx = self.fld.bdx*1.5
        self.fld.bzx = self.anc.real_constants.start_lon - self.fld.bdx
        self.anc.fields = [self.fld]
        self.anc.validate()

    # Test upper boundary x value just outside tolerance fails
    def test_basic_regular_max_x_fail(self):
        self.fld.bdx = self.fld.bdx*1.51
        self.fld.bzx = self.anc.real_constants.start_lon - self.fld.bdx
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'longitudes inconsistent'):
            self.anc.validate()

    # Test lower boundary y value just within tolerance passes
    def test_basic_regular_min_y_ok(self):
        self.fld.bzy += self.fld.bdy * (1.01 - 0.0001)
        self.fld.lbrow -= 1
        self.anc.fields = [self.fld]
        self.anc.validate()

    # Test lower boundary y value just outside tolerance fails
    def test_basic_regular_min_y_fail(self):
        self.fld.bzy += self.fld.bdy * (1.01 + 0.0001)
        self.fld.lbrow -= 1
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'latitudes inconsistent'):
            self.anc.validate()

    # Test upper boundary y value just within tolerance passes
    def test_basic_regular_max_y_ok(self):
        self.fld.bdy = self.fld.bdy*2.02
        self.fld.bzy = self.anc.real_constants.start_lat - self.fld.bdy
        self.anc.fields = [self.fld]
        self.anc.validate()

    # Test upper boundary y value just outside tolerance fails
    def test_basic_regular_max_y_fail(self):
        self.fld.bdy = self.fld.bdy*2.03
        self.fld.bzy = self.anc.real_constants.start_lat - self.fld.bdy
        self.anc.fields = [self.fld]
        with six.assertRaisesRegex(self,
                                   ValueError, 'latitudes inconsistent'):
            self.anc.validate()


if __name__ == '__main__':
    tests.main()
