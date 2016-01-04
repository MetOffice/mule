# (C) Crown Copyright 2016, Met Office. All rights reserved.
#
# This file is part of the UM utilities module, which use the Mule API.
#
# Mule and these utilities are free software: you can redistribute it and/or
# modify them under the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# These utilities are distributed in the hope that they will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with these utilities.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""Tests for the :mod:`um_utils` module."""

from __future__ import (absolute_import, division, print_function)

import numpy as np
import unittest as tests

import mule

class UMUtilsTest(tests.TestCase):
    """An extension of unittest.TestCase with extra test methods."""

    # Some simple default options for field dimensions
    _dflt_nx = 4
    _dflt_ny = 3
    _dflt_nz = 5
    _dflt_x0 = 10.0
    _dflt_dx = 0.1
    _dflt_y0 = -60.0
    _dflt_dy = 0.2

    def assertArrayEqual(self, a, b, err_msg=''):
        """Check that numpy arrays have identical contents."""
        np.testing.assert_array_equal(a, b, err_msg=err_msg)

    def assertArrayLess(self, a, b, err_msg=''):
        """Check that numpy array is less than value."""
        np.testing.assert_array_less(a, b, err_msg=err_msg)        

    def assertLinesEqual(self, line1, line2):
        """Check two output lines are equal."""
        self.assertEqual(line1, line2,
            "Lines not equal:\nFound:\n  '{0}'\nExpected:\n  '{1}'"
            .format(line1, line2))        

    @staticmethod
    def _minimal_valid_ff(nx=_dflt_nx, ny=_dflt_ny, nz=_dflt_nz,
                          x0=_dflt_x0, dx=_dflt_dx, y0=_dflt_y0, dy=_dflt_dy):
        # Construct a mock 'minimal' file that passes the validation tests.
        ff = mule.FieldsFile()
        ff.fixed_length_header.dataset_type = 3
        ff.fixed_length_header.grid_staggering = 3
        ff.integer_constants = mule.ff.FF_IntegerConstants.empty()
        ff.integer_constants.num_cols = nx
        ff.integer_constants.num_rows = ny
        ff.integer_constants.num_p_levels = nz
        ff.real_constants = mule.ff.FF_RealConstants.empty()
        ff.real_constants.start_lon = x0
        ff.real_constants.col_spacing = dx
        ff.real_constants.start_lat = y0
        ff.real_constants.row_spacing = dy

        ff.level_dependent_constants = (
            mule.ff.FF_LevelDependentConstants.empty(nz + 1))
        ldc_range = np.arange(nz + 1)
        for idim in range(1, ff.level_dependent_constants.shape[1] + 1):
            ff.level_dependent_constants.raw[:, idim] = ldc_range*idim

        return ff

    @staticmethod
    def _minimal_valid_field(nx=_dflt_nx, ny=_dflt_ny,
                             x0=_dflt_x0, dx=_dflt_dx,
                             y0=_dflt_y0, dy=_dflt_dy):
        # Construct a mock 'minimal' field that passes the validation tests.
        fld = mule.Field3.empty()
        fld.lbrel = 3
        fld.lbrow = ny
        fld.bzy = y0
        fld.bdy = dy
        fld.lbnpt = nx
        fld.bzx = x0
        fld.bdx = dx
        provider = mule.ArrayDataProvider(np.arange(nx*ny).reshape(nx,ny))
        fld.set_data_provider(provider)
        return fld    

def main():
    """
    A wrapper that just calls unittest.main().

    Allows um_packing.tests to be imported in place of unittest

    """
    tests.main()    
