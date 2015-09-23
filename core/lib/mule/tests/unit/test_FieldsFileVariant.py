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

import mule.tests as tests

from mule import UMFile, Field, Field3

try:
    import mo_pack
except ImportError:
    # Disable all these tests if mo_pack is not installed.
    mo_pack = None

skip_mo_pack = unittest.skipIf(mo_pack is None,
                               'Test(s) require "mo_pack", '
                               'which is not available.')


class Test___init__(tests.MuleTest):
    def test_invalid_mode(self):
        with self.assertRaisesRegexp(ValueError, 'access mode'):
            UMFile('/fake/path', mode='g')

    def test_missing_file(self):
        dir_path = tempfile.mkdtemp()
        try:
            file_path = os.path.join(dir_path, 'missing')
            with self.assertRaisesRegexp(IOError, 'No such file'):
                UMFile(file_path, mode=UMFile.READ_MODE)
        finally:
            shutil.rmtree(dir_path)

    def test_new_file(self):
        with self.temp_filename() as temp_path:
            ffv = UMFile(temp_path, mode=UMFile.CREATE_MODE)
            self.assertArrayEqual(ffv.fixed_length_header.raw,
                                  [None] + [-32768] * 256)
            self.assertIsNone(ffv.integer_constants)
            self.assertIsNone(ffv.real_constants)
            self.assertIsNone(ffv.level_dependent_constants)
            self.assertIsNone(ffv.row_dependent_constants)
            self.assertIsNone(ffv.column_dependent_constants)

            # Disabled because: these attributes no longer exist, they may
            #                   return at some point but for now are absent
            # self.assertIsNone(ffv.fields_of_constants)
            # self.assertIsNone(ffv.extra_constants)
            # self.assertIsNone(ffv.temp_historyfile)
            # self.assertIsNone(ffv.compressed_field_index1)
            # self.assertIsNone(ffv.compressed_field_index2)
            # self.assertIsNone(ffv.compressed_field_index3)

            self.assertEqual(ffv.fields, [])
            del ffv


class Test_filename(tests.MuleTest):
    def test(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = UMFile(path)
        self.assertEqual(ffv.filename, path)


# class Test_class_assignment(tests.MuleTest):
#     @skip_mo_pack
#     def test_lbrel_class(self):
#         path = tests.testfile_datapath('lbrel_test_data.ff')
#         ffv = UMFile(path)
#         self.assertEqual(type(ffv.fields[0]), Field)
#         self.assertEqual(type(ffv.fields[1]), Field3)
#         self.assertEqual(ffv.fields[0].int_headers[Field.LBREL_OFFSET],
#                          -32768)
#         self.assertEqual(ffv.fields[1].int_headers[Field.LBREL_OFFSET], 3)


class Test_mode(tests.MuleTest):
    def test_read(self):
        path = tests.testfile_datapath('n48_multi_field.ff')
        ffv = UMFile(path)
        self.assertIs(ffv.mode, UMFile.READ_MODE)

    def test_append(self):
        src_path = tests.testfile_datapath('n48_multi_field.ff')
        with self.temp_filename() as temp_path:
            shutil.copyfile(src_path, temp_path)
            ffv = UMFile(temp_path, mode=UMFile.UPDATE_MODE)
            self.assertIs(ffv.mode, UMFile.UPDATE_MODE)
            del ffv

    def test_write(self):
        with self.temp_filename() as temp_path:
            ffv = UMFile(temp_path, mode=UMFile.CREATE_MODE)
            self.assertIs(ffv.mode, UMFile.CREATE_MODE)
            del ffv


if __name__ == '__main__':
    tests.main()
