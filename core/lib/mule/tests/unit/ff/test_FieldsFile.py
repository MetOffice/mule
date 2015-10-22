# (C) Crown Copyright 2015, Met Office. All rights reserved.
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
from six.moves import (filter, input, map, range, zip)  # noqa


import mule.tests as tests
from mule.tests import check_common_n48_testdata, COMMON_N48_TESTDATA_PATH

from mule import FieldsFile, Field3
from mule.ff import (FF_IntegerConstants, FF_RealConstants,
                     FF_LevelDependentConstants, ValidateError)


class Test___init__(tests.MuleTest):
    """Check FieldsFile __init__ method."""
    def test_new_fieldsfile(self):
        ffv = FieldsFile()
        self.assertArrayEqual(ffv.fixed_length_header.raw,
                              [None] + [-32768] * 256)

        # NOTE: some of these are WRONG -- it should be able to create them...
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
        # NOTE: arguably, the bare init() should do this, too...
        # Our current implementation doesn't (see Test___init__, above).
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
        fld.lbrow = ny
        fld.bzy = y0
        fld.bdy = dy
        fld.lbnpt = nx
        fld.bzx = x0
        fld.bdx = dx
        return fld

    def test_basic_ok(self):
        ff = self._minimal_valid_ff()
        ff.validate()

    def test_baddims_example__fail(self):
        nz, ny, nx = 5, 4, 3
        ff = self._minimal_valid_ff(nx, ny, nz)
        ff.real_constants = FF_RealConstants.empty(3)
        with self.assertRaisesRegexp(ValidateError,
                                     'real constants.*3.*should be.*38'):
            ff.validate()

    def test_basic_field(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        ff.fields = [fld]
        ff.validate()

    def test_tolerance_max_x__ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.51 - 0.0001)
        ff.fields = [fld]
        ff.validate()

    def test_tolerance_min_x__fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzx += fld.bdx * (1.51 + 0.0001)
        ff.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'longitude'):
            ff.validate()

    def test_tolerance_max_y__ok(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.51 - 0.0001)
        ff.fields = [fld]
        ff.validate()

    def test_tolerance_min_y__fail(self):
        ff = self._minimal_valid_ff()
        fld = self._minimal_valid_field()
        fld.bzy += fld.bdy * (1.51 + 0.0001)
        ff.fields = [fld]
        with self.assertRaisesRegexp(ValueError, 'latitude'):
            ff.validate()


if __name__ == '__main__':
    tests.main()
