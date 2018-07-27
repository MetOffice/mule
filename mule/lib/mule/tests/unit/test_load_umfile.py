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
Unit tests for :class:`mule.load_umfile`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import mule.tests as tests
from mule.tests import check_common_n48_testdata, COMMON_N48_TESTDATA_PATH

from mule import FieldsFile, LBCFile, load_umfile


class Test_load_umfile(tests.MuleTest):
    def test_fieldsfile_bypath(self):
        ffv = load_umfile(COMMON_N48_TESTDATA_PATH)
        self.assertEqual(type(ffv), FieldsFile)
        check_common_n48_testdata(self, ffv)

    def test_fieldsfile_byfile(self):
        with open(COMMON_N48_TESTDATA_PATH) as open_file:
            ffv = load_umfile(open_file)
        self.assertEqual(type(ffv), FieldsFile)
        check_common_n48_testdata(self, ffv)

if __name__ == '__main__':
    tests.main()
