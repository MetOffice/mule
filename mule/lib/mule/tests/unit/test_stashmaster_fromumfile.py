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
Unit tests for :class:`mule.stashmaster`.

"""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

import mule.tests as tests
from mule.stashmaster import STASHmaster

import six
if six.PY2:
    from mock import patch
elif six.PY3:
    from unittest.mock import patch


class FakeFixedLength(object):
    def __init__(self, dataset_type, model_version, mdi):
        self.dataset_type = dataset_type
        self.model_version = model_version
        self.MDI = mdi


class TestStashmasterFromUmfile(tests.MuleTest):

    def test_fromumfile_mdi_version(self):
        self.fixed_length_header = FakeFixedLength(1, -99, -99)
        with patch('warnings.warn') as warn:
            STASHmaster.from_umfile(self)
            expected_msg = ('Fixed length header does not define the UM model '
                            'version number, unable to load STASHmaster file.')
            warn.assert_called_once_with(expected_msg)

    def test_fromfile_ancil(self):
        self.fixed_length_header = FakeFixedLength(4, 1003, -99)
        with patch('warnings.warn') as warn:
            STASHmaster.from_umfile(self)
            expected_msg = ('Ancillary files do not define the UM version '
                            'number in the Fixed Length Header. '
                            'No STASHmaster file loaded: Fields will not '
                            'have STASH entries attached.')
            warn.assert_called_once_with(expected_msg)

    def test_fromumfile_non_ancil(self):
        self.fixed_length_header = FakeFixedLength(1, 1003, -99)
        to_patch = 'mule.stashmaster.STASHmaster.from_version'
        with patch(to_patch) as from_version:
            STASHmaster.from_umfile(self)
            from_version.assert_called_once_with('10.3')


if __name__ == '__main__':
    tests.main()
