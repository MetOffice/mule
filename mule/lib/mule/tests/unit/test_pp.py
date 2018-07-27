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
Unit tests for :module:`mule.pp`.

"""

from __future__ import (absolute_import, division, print_function)

import mule
import mule.tests as tests
from mule.tests import testdata_filepath
from mule.pp import fields_from_pp_file, fields_to_pp_file


class Test_load_fields(tests.MuleTest):
    """Test the reading of different files"""
    def test_pp_file_format_check(self):

        pp_file = testdata_filepath("n48_multi_field.pp")
        self.assertTrue(mule.pp.file_is_pp_file(pp_file))

        um_file = testdata_filepath("n48_multi_field.ff")
        self.assertFalse(mule.pp.file_is_pp_file(um_file))

        um_file = testdata_filepath("soil_params.anc")
        self.assertFalse(mule.pp.file_is_pp_file(um_file))

        um_file = testdata_filepath("eg_boundary_sample.lbc")
        self.assertFalse(mule.pp.file_is_pp_file(um_file))

        um_file = testdata_filepath("n48_eg_dump_special.dump")
        self.assertFalse(mule.pp.file_is_pp_file(um_file))

    def test_read_ppfile_fix_grid(self, fname=None):

        if fname is None:
            fname = testdata_filepath("n48_multi_field.pp")

        pp = fields_from_pp_file(fname)
        self.assertEqual(len(pp), 4)

        expected_rel = (3, 3, 3, 3)
        expected_vc = (1, 1, 6, 129)

        for field, rel, vc in zip(pp,
                                  expected_rel,
                                  expected_vc):
            self.assertIsNone(field.pp_extra_data)
            self.assertEqual(field.lbrel, rel)
            self.assertEqual(field.lbvc, vc)

            data = field.get_data()
            self.assertEqual(data.shape[0], field.lbrow)
            self.assertEqual(data.shape[1], field.lbnpt)

    def test_read_ppfile_var_grid(self, fname=None):

        if fname is None:
            fname = testdata_filepath("ukv_eg_variable_sample.pp")

        pp = fields_from_pp_file(fname)
        self.assertEqual(len(pp), 1)

        field = pp[0]

        self.assertIsNotNone(field.pp_extra_data)
        self.assertEqual(field.lbrel, 3)
        self.assertEqual(field.lbvc, 65)

        data = field.get_data()
        self.assertEqual(data.shape[0], field.lbrow)
        self.assertEqual(data.shape[1], field.lbnpt)

        expected_extra = [1, 2, 12, 13, 14, 15]
        self.assertEqual(len(field.pp_extra_data), 6)
        self.assertArrayEqual(list(field.pp_extra_data.keys()),
                              expected_extra)

        self.assertEqual(len(field.pp_extra_data[1]), field.lbnpt)
        self.assertEqual(len(field.pp_extra_data[12]), field.lbnpt)
        self.assertEqual(len(field.pp_extra_data[13]), field.lbnpt)

        self.assertEqual(len(field.pp_extra_data[2]), field.lbrow)
        self.assertEqual(len(field.pp_extra_data[14]), field.lbrow)
        self.assertEqual(len(field.pp_extra_data[15]), field.lbrow)

    def test_ff_to_pp_fix_grid(self):
        ff = mule.FieldsFile.from_file(
            testdata_filepath("n48_multi_field.ff"))

        with self.temp_filename() as temp_path:
            fields_to_pp_file(temp_path, ff.fields)
            # Re-read
            self.test_read_ppfile_fix_grid(temp_path)

    def test_ff_to_pp_var_grid(self):
        ff = mule.FieldsFile.from_file(
            testdata_filepath("ukv_eg_variable_sample.ff"))

        with self.temp_filename() as temp_path:
            fields_to_pp_file(temp_path, ff.fields, ff)
            # Re-read
            self.test_read_ppfile_var_grid(temp_path)


if __name__ == '__main__':
    tests.main()
