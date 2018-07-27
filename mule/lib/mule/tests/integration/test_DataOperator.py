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
Unit tests for :class:`mule.Field`.

"""

from __future__ import (absolute_import, division, print_function)

import mule.tests as tests

from mule import FieldsFile, DataOperator


class XSampler(DataOperator):
    def __init__(self, factor):
        self.factor = factor

    def new_field(self, source_field):
        fld = source_field.copy()
        fld.lbnpt = fld.lbnpt // self.factor
        fld.bzx += fld.bdx - fld.bdx*self.factor
        fld.bdx *= self.factor
        return fld

    def transform(self, source_field, result_field):
        data = source_field.get_data()
        return data[:, ::self.factor]


class Test_Subsample(tests.MuleTest):
    def test(self):
        ff = FieldsFile.from_file(tests.COMMON_N48_TESTDATA_PATH)
        num_cols = ff.integer_constants.num_cols
        col_spacing = ff.real_constants.col_spacing
        self.assertEqual(num_cols, 96)
        self.assertEqual(col_spacing, 3.75)
        self.assertEqual(ff.fields[0].lbnpt, num_cols)
        self.assertEqual(ff.fields[0].bdx, col_spacing)
        XStep4 = XSampler(factor=4)
        ff.fields = [XStep4(ff.fields[0]), XStep4(ff.fields[1])]
        ff.integer_constants.num_cols = num_cols // 4
        ff.real_constants.col_spacing = col_spacing*4
        with self.temp_filename() as temp_path:
            ff.to_file(temp_path)
            ff_back = FieldsFile.from_file(temp_path)
            self.assertEqual(ff_back.integer_constants.num_cols, num_cols // 4)
            self.assertEqual(ff_back.real_constants.col_spacing, col_spacing*4)
            self.assertEqual(ff_back.fields[0].lbnpt, num_cols // 4)
            self.assertEqual(ff_back.fields[0].bdx, col_spacing*4)
            self.assertEqual(ff_back.fields[1].lbnpt, num_cols//4)
            self.assertEqual(ff_back.fields[1].bdx, col_spacing*4)
            self.assertEqual(ff_back.fields[1].get_data().shape, (73, 24))


if __name__ == '__main__':
    tests.main()
