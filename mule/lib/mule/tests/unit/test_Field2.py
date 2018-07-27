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
Unit tests for :class:`mule.Field2`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import numpy as np

import mule.tests as tests

from mule import Field2


def make_field():
    headers = (np.arange(64) + 1) * 10
    return Field2(headers[:45], headers[45:], None)


class Test_lbyr(tests.MuleTest):
    def test(self):
        field = make_field()
        self.assertEqual(field.lbyr, 10)


class Test_lbmon(tests.MuleTest):
    def test(self):
        field = make_field()
        self.assertEqual(field.lbmon, 20)


class Test_lbday(tests.MuleTest):
    def test(self):
        field = make_field()
        self.assertEqual(field.lbday, 60)


class Test_lbrsvd1(tests.MuleTest):
    def test(self):
        field = make_field()
        self.assertEqual(field.lbrsvd1, 340)


class Test_lbrsvd4(tests.MuleTest):
    def test(self):
        field = make_field()
        self.assertEqual(field.lbrsvd4, 370)


class Test_lbuser7(tests.MuleTest):
    def test(self):
        field = make_field()
        self.assertEqual(field.lbuser7, 450)


class Test_bdx(tests.MuleTest):
    def test(self):
        field = make_field()
        self.assertEqual(field.bdx, 620)


if __name__ == '__main__':
    tests.main()
