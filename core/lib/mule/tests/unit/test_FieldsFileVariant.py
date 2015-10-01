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
Unit tests for :class:`mule.FieldsFileVariant`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa


import os.path
import shutil
import tempfile
import unittest

import numpy as np

import mule.tests as tests

from mule import UMFile, Field, Field3, FieldsFile, load_umfile

try:
    import mo_pack
except ImportError:
    # Disable all these tests if mo_pack is not installed.
    mo_pack = None

skip_mo_pack = unittest.skipIf(mo_pack is None,
                               'Test(s) require "mo_pack", '
                               'which is not available.')


class Test___init__(tests.MuleTest):
#    def test_invalid_mode(self):
#        with self.assertRaisesRegexp(ValueError, 'access mode'):
#            UMFile('/fake/path', mode='g')

    def test_missing_file(self):
        dir_path = tempfile.mkdtemp()
        try:
            file_path = os.path.join(dir_path, 'missing')
            with self.assertRaisesRegexp(IOError, 'No such file'):
                UMFile.from_file(file_path)
        finally:
            shutil.rmtree(dir_path)

    def test_new(self):
        ffv = UMFile()
        self.assertArrayEqual(ffv.fixed_length_header.raw,
                              [None] + [-32768] * 256)
        self.assertIsNone(ffv.integer_constants)
        self.assertIsNone(ffv.real_constants)
        self.assertIsNone(ffv.level_dependent_constants)
        self.assertIsNone(ffv.row_dependent_constants)
        self.assertIsNone(ffv.column_dependent_constants)
        self.assertEqual(ffv.fields, [])
        del ffv

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


# class Test_class_assignment(tests.MuleTest):
#     @skip_mo_pack
#     def test_lbrel_class(self):
#         path = tests.get_file_datapath('lbrel_test_data.ff')
#         ffv = UMFile(path)
#         self.assertEqual(type(ffv.fields[0]), Field)
#         self.assertEqual(type(ffv.fields[1]), Field3)
#         self.assertEqual(ffv.fields[0].int_headers[Field.LBREL_OFFSET],
#                          -32768)
#         self.assertEqual(ffv.fields[1].int_headers[Field.LBREL_OFFSET], 3)


class Test_mode(tests.MuleTest):
    def _known_content_checks(self, ffv):
        # Test for some known content properties.
        self.assertIsNotNone(ffv.integer_constants)
        self.assertEqual(ffv.integer_constants.shape, (46,))
        self.assertIsNotNone(ffv.real_constants)
        self.assertEqual(ffv.real_constants.shape, (38,))
        self.assertIsNotNone(ffv.level_dependent_constants)
        self.assertIsNone(ffv.row_dependent_constants)
        self.assertIsNone(ffv.column_dependent_constants)
        self.assertEqual(len(ffv.fields), 5)
        self.assertEqual([fld.lbrel for fld in ffv.fields[:-1]],
                         [3, 3, 3, 3])
        self.assertEqual(type(ffv.fields[-1]), Field)
        self.assertEqual([fld.lbvc for fld in ffv.fields[:-1]],
                         [1, 1, 6, 129])

    def test_read_umfile(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = UMFile.from_file(path)
        self.assertEqual(type(ffv), UMFile)
        self._known_content_checks(ffv)

    def test_read_fieldsfile(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = FieldsFile.from_file(path)
        self.assertEqual(type(ffv), FieldsFile)
        self._known_content_checks(ffv)

    def test_load_umfile_path(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = load_umfile(path)
        self.assertEqual(type(ffv), FieldsFile)
        self._known_content_checks(ffv)

    def test_load_umfile_file(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        with open(path) as open_file:
            ffv = load_umfile(open_file)
        self.assertEqual(type(ffv), FieldsFile)
        self._known_content_checks(ffv)


#    def test_append(self):
#        src_path = tests.testfile_datapath('n48_multi_field.ff')
#        with self.temp_filename() as temp_path:
#            shutil.copyfile(src_path, temp_path)
#            ffv = UMFile(temp_path, mode=UMFile.UPDATE_MODE)
#            self.assertIs(ffv.mode, UMFile.UPDATE_MODE)
#            del ffv

#    def test_write_empty(self):
#        with self.temp_filename() as temp_path:
#            ffv = UMFile()
#            ffv.to_file(temp_path)

    def test_write_copy_byfile(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = UMFile.from_file(path)
        with self.temp_filename() as temp_path:
            with open(temp_path, 'w') as temp_file:
                ffv.to_file(temp_file)
            assert os.path.exists(temp_path)
            # Read it back and repeat our basic "known content" tests
            ffv_rb = FieldsFile.from_file(temp_path)
            self.assertIsNotNone(ffv_rb.integer_constants)
            self.assertIsNotNone(ffv_rb.real_constants)
            self.assertIsNotNone(ffv_rb.level_dependent_constants)
            self.assertIsNone(ffv_rb.row_dependent_constants)
            self.assertIsNone(ffv_rb.column_dependent_constants)
            self.assertEqual(len(ffv_rb.fields), 5)
            self.assertEqual([fld.lbrel for fld in ffv_rb.fields[:-1]],
                             [3, 3, 3, 3])
            self.assertEqual(type(ffv_rb.fields[-1]), Field)
            self.assertEqual([fld.lbvc for fld in ffv_rb.fields[:-1]],
                             [1, 1, 6, 129])

    def test_write_copy_bypath(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = UMFile.from_file(path)
        with self.temp_filename() as temp_path:
            ffv.to_file(temp_path)
            assert os.path.exists(temp_path)
            # Read it back and repeat our basic "known content" tests
            ffv_rb = FieldsFile.from_file(temp_path)
            self.assertIsNotNone(ffv_rb.integer_constants)
            self.assertIsNotNone(ffv_rb.real_constants)
            self.assertIsNotNone(ffv_rb.level_dependent_constants)
            self.assertIsNone(ffv_rb.row_dependent_constants)
            self.assertIsNone(ffv_rb.column_dependent_constants)
            self.assertEqual(len(ffv_rb.fields), 5)
            self.assertEqual([fld.lbrel for fld in ffv_rb.fields[:-1]],
                             [3, 3, 3, 3])
            self.assertEqual(type(ffv_rb.fields[-1]), Field)
            self.assertEqual([fld.lbvc for fld in ffv_rb.fields[:-1]],
                             [1, 1, 6, 129])

    @staticmethod
    def _template_from_existing(ffv):
        #
        # This could be an interesting utility function.
        # Maybe it shouldn't print the array values, though ?
        #
        names = [name for name, _ in ffv._COMPONENTS]
        names = ['fixed_length_header'] + names
        result = '\n{'
        for name in names:
            result += '\n "{}":'.format(name)
            comp = getattr(ffv, name, None)
            if not comp:
                result += 'None,\n'
            else:
                dictstr = '\n    {'
                any_done = False
                for name, _ in getattr(comp, 'HEADER_MAPPING', []):
                    value = getattr(comp, name)
                    if isinstance(value, np.ndarray) or value != comp.MDI:
                        msg = '\n     "{}":{!r},'
                        dictstr += msg.format(name, value)
                        any_done = True
                dictstr += '\n    },\n' if  any_done else '},\n'
                result += dictstr
        result += '\n}\n'
        return result

    def test_template_from_existing(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = FieldsFile.from_file(path)
        print(self._template_from_existing(ffv))

    def test_fieldsfile_minimal_template(self):
        test_template = {"integer_constants": {}}
        ffv = FieldsFile.from_template(test_template)
        self.assertEqual(ffv.integer_constants.shape, (46,))
        self.assertIsNone(ffv.real_constants)

    def test_fieldsfile_template_sizing(self):
        test_template = {"real_constants": {'dims':(9,)}}
        ffv = FieldsFile.from_template(test_template)
        self.assertEqual(ffv.real_constants.shape, (9,))
        self.assertIsNone(ffv.integer_constants)

    def test_no_size_defaults__template__umfile(self):
        test_template = {"integer_constants": {}}
        with self.assertRaisesRegexp(ValueError,
                                     '"num_words" has no valid default'):
            _ = UMFile.from_template(test_template)

    def test_create_from_template(self):
        test_template = {
             "fixed_length_header":
                {
                 "data_set_format_version":20,
                 "sub_model":1,
                 "vert_coord_type":5,
                 "horiz_grid_type":0,
                 "dataset_type":3,
                 "run_identifier":0,
                 "calendar":1,
                 "grid_staggering":3,
                 "model_version":802,
                },
             "integer_constants":
                {
                 "num_cols":96,
                 "num_rows":73,
                 "num_p_levels":70,
                 "num_wet_levels":70,
                 "num_soil_levels":4,
                 "num_tracer_levels":70,
                 "num_boundary_levels":50,
                 "height_algorithm":2,
                 "first_constant_rho":50,
                 "num_land_points":2381,
                 "num_soil_hydr_levels":4,
                },
             "real_constants":
                {
                 "col_spacing":3.75,
                 "row_spacing":2.5,
                 "start_lat":-90.0,
                 "start_lon":0.0,
                 "north_pole_lat":90.0,
                 "north_pole_lon":0.0,
                 "top_theta_height":80000.0,
                },
             "level_dependent_constants":
                {'dims':(70,),  # this one absolutely *is* needed
                 },
            }
        ff_new = FieldsFile.from_template(test_template)
        with self.temp_filename() as temp_path:
            ff_new.to_file(temp_path)
            ffv_reload = FieldsFile.from_file(temp_path)
        self.assertIsNone(ffv_reload.row_dependent_constants)
        self.assertIsNone(ffv_reload.column_dependent_constants)
        self.assertEqual(ffv_reload.level_dependent_constants.raw.shape,
                         (70, 9))

    def test_fieldsfile_minimal_create(self):
        # NOTE: arguably, the bare init() should do this, too...
        # The current usage of 'get_position' doesn't enable that.
        ffv = FieldsFile.from_template({'integer_constants':{}, 
                                        'real_constants':{}, })
        self.assertEqual(ffv.integer_constants.shape, (46,))
        self.assertEqual(ffv.real_constants.shape, (38,))


if __name__ == '__main__':
    tests.main()
