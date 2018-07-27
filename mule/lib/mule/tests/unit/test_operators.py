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
Unit tests for the built-in :class:`mule.DataOperator` subclasses.

"""

from __future__ import (absolute_import, division, print_function)

import numpy as np

import mule.tests as tests
import mule.operators as operators
from mule import Field3, ArrayDataProvider


class Test_operators(tests.MuleTest):

    MDI = -1234.0

    # Create a field object from a data array; this only needs to be very
    # basic to provide something suitable to test the operators
    def _field_from_data(self, data):
        fld = Field3.empty()
        fld.lbrel = 3
        fld.lbrow = data.shape[0]
        fld.lbnpt = data.shape[1]
        fld.bmdi = self.MDI
        provider = ArrayDataProvider(data)
        fld.set_data_provider(provider)
        return fld

    def run_operator_test(self, data, operator, valid):
        if hasattr(data, "shape"):
            # Single array argument
            fld = self._field_from_data(data)
            new_field = operator(fld)
        else:
            # Multi-array argument
            flds = []
            for array in data:
                flds.append(self._field_from_data(array))
                provider = ArrayDataProvider(array)
                flds[-1].set_data_provider(provider)
            new_field = operator(flds)

        # Retrieve the transformed data and compare it to the valid data
        self.assertArrayEqual(new_field.get_data(), valid)

    # Test typical usage of operator to add to a field
    def test_AddScalarOperator_add(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.AddScalarOperator(50.0)
        valid = data + 50.0
        self.run_operator_test(data, operator, valid)

    # Test typical usage of operator to subtract from a field
    def test_AddScalarOperator_subtract(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.AddScalarOperator(-50.0)
        valid = data - 50.0
        self.run_operator_test(data, operator, valid)

    # Test typical usage of operator to add to a field, with mdi points
    def test_AddScalarOperator_mdi(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        data[2, 2] = self.MDI
        operator = operators.AddScalarOperator(50.0)
        valid = data + 50.0
        valid[2, 2] = self.MDI
        self.run_operator_test(data, operator, valid)

    # Test typical usage of operator to multiply a field
    def test_ScaleFactorOperator_multiply(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.ScaleFactorOperator(3.0)
        valid = data * 3.0
        self.run_operator_test(data, operator, valid)

    # Test typical usage of operator to divide a field
    def test_ScaleFactorOperator_divide(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.ScaleFactorOperator(0.5)
        valid = data * 0.5
        self.run_operator_test(data, operator, valid)

    # Test typical usage of operator to multiply a field, with mdi points
    def test_ScaleFactorOperator_mdi(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        data[2, 2] = self.MDI
        operator = operators.ScaleFactorOperator(3.0)
        valid = data * 3.0
        valid[2, 2] = self.MDI
        self.run_operator_test(data, operator, valid)

    # Test limit operator lower limit only
    def test_HardLimitOperator_lower(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.HardLimitOperator(lower_limit=4.0)
        valid = data.copy()
        valid[data < 4.0] = 4.0
        self.run_operator_test(data, operator, valid)

    # Test limit operator upper limit only
    def test_HardLimitOperator_upper(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.HardLimitOperator(upper_limit=8.0)
        valid = data.copy()
        valid[data > 8.0] = 8.0
        self.run_operator_test(data, operator, valid)

    # Test limit operator lower and upper limits
    def test_HardLimitOperator_both(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.HardLimitOperator(lower_limit=3.0,
                                               upper_limit=9.0)
        valid = data.copy()
        valid[data < 3.0] = 3.0
        valid[data > 9.0] = 9.0
        self.run_operator_test(data, operator, valid)

    # Test limit operator lower and upper limits with fill values
    def test_HardLimitOperator_both(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.HardLimitOperator(lower_limit=3.0,
                                               lower_fill=99.0,
                                               upper_limit=9.0,
                                               upper_fill=123.0)
        valid = data.copy()
        valid[data < 3.0] = 99.0
        valid[data > 9.0] = 123.0
        self.run_operator_test(data, operator, valid)

    # Test limit operator lower and upper limits with fill values and mdi
    def test_HardLimitOperator_both_mdi(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.HardLimitOperator(lower_limit=3.0,
                                               lower_fill=99.0,
                                               upper_limit=9.0,
                                               upper_fill=123.0)
        data[2, 2] = self.MDI
        valid = data.copy()
        valid[data < 3.0] = 99.0
        valid[data > 9.0] = 123.0
        valid[2, 2] = self.MDI
        self.run_operator_test(data, operator, valid)

    # Test value exchange operator on non-mdi value
    def test_ValueExchangeOperator_non_mdi(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        operator = operators.ValueExchangeOperator(5.0, 123.0)
        valid = data.copy()
        valid[1, 2] = 123.0
        self.run_operator_test(data, operator, valid)

    # Test value exchange operator on mdi value
    def test_ValueExchangeOperator_mdi(self):
        data = np.arange(12, dtype="float").reshape(4, 3)
        data[2, 2] = self.MDI
        operator = operators.ValueExchangeOperator(self.MDI, 123.0)
        valid = data.copy()
        valid[2, 2] = 123.0
        self.run_operator_test(data, operator, valid)

    # Test adding multiple fields together
    def test_AddFieldsOperator(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data = [data1, data2, data3]
        operator = operators.AddFieldsOperator()
        valid = data1 + data2 + data3
        self.run_operator_test(data, operator, valid)

    # Test adding multiple fields together, with mdi points preserved
    def test_AddFieldsOperator_preserve_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.AddFieldsOperator()
        valid = data1 + data2 + data3
        valid[2, 2] = self.MDI
        self.run_operator_test(data, operator, valid)

    # Test adding multiple fields together, with mdi points not preserved
    def test_AddFieldsOperator_no_preserve_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.AddFieldsOperator(preserve_mdi=False)
        valid = data1 + data2 + data3
        self.run_operator_test(data, operator, valid)

    # Test adding multiple fields together, alternative mdi value
    def test_AddFieldsOperator_alternative_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.AddFieldsOperator(mdi_val=15.0)
        valid = data1 + data2 + data3
        valid[1, 0] = 15.0
        self.run_operator_test(data, operator, valid)

    # Test subtraction of multiple fields
    def test_SubtractFieldsOperator(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data = [data1, data2, data3]
        operator = operators.SubtractFieldsOperator()
        valid = data1 - data2 - data3
        self.run_operator_test(data, operator, valid)

    # Test subtracting multiple fields, with mdi points preserved
    def test_SubtractFieldsOperator_preserve_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.SubtractFieldsOperator()
        valid = data1 - data2 - data3
        valid[2, 2] = self.MDI
        self.run_operator_test(data, operator, valid)

    # Test subtracting multiple fields, with mdi points not preserved
    def test_SubtractFieldsOperator_no_preserve_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.SubtractFieldsOperator(preserve_mdi=False)
        valid = data1 - data2 - data3
        self.run_operator_test(data, operator, valid)

    # Test subtracting multiple fields, alternative mdi value
    def test_SubtractFieldsOperator_alternative_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.SubtractFieldsOperator(mdi_val=15.0)
        valid = data1 - data2 - data3
        valid[1, 0] = 15.0
        self.run_operator_test(data, operator, valid)

    # Test multiplying fields
    def test_MultiplyFieldsOperator(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data = [data1, data2, data3]
        operator = operators.MultiplyFieldsOperator()
        valid = data1 * data2 * data3
        self.run_operator_test(data, operator, valid)

    # Test multiplying fields, with mdi points preserved
    def test_MultiplyFieldsOperator_preserve_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.MultiplyFieldsOperator()
        valid = data1 * data2 * data3
        valid[2, 2] = self.MDI
        self.run_operator_test(data, operator, valid)

    # Test multiplying fields, with mdi points not preserved
    def test_MultiplyFieldsOperator_no_preserve_mdi(self):
        data1 = np.arange(12).reshape(4, 3)
        data2 = np.arange(12, 24).reshape(4, 3)
        data3 = np.arange(24, 36).reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.MultiplyFieldsOperator(preserve_mdi=False)
        valid = data1 * data2 * data3
        self.run_operator_test(data, operator, valid)

    # Test multiplying fields, alternative mdi value
    def test_MultiplyFieldsOperator_alternative_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.MultiplyFieldsOperator(mdi_val=15.0)
        valid = data1 * data2 * data3
        valid[1, 0] = 15.0
        self.run_operator_test(data, operator, valid)

    # Test dividing fields
    def test_DivideFieldsOperator(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data = [data1, data2, data3]
        operator = operators.DivideFieldsOperator()
        valid = data1 / data2 / data3
        self.run_operator_test(data, operator, valid)

    # Test dividing fields, with mdi points preserved
    def test_DivideFieldsOperator_preserve_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.DivideFieldsOperator()
        valid = data1 / data2 / data3
        valid[2, 2] = self.MDI
        self.run_operator_test(data, operator, valid)

    # Test dividing fields, with mdi points not preserved
    def test_DivideFieldsOperator_no_preserve_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.DivideFieldsOperator(preserve_mdi=False)
        valid = data1 / data2 / data3
        self.run_operator_test(data, operator, valid)

    # Test dividing fields, alternative mdi value
    def test_DivideFieldsOperator_alternative_mdi(self):
        data1 = np.arange(12, dtype="float").reshape(4, 3)
        data2 = np.arange(12, 24, dtype="float").reshape(4, 3)
        data3 = np.arange(24, 36, dtype="float").reshape(4, 3)
        data1[2, 2] = self.MDI
        data = [data1, data2, data3]
        operator = operators.DivideFieldsOperator(mdi_val=15.0)
        valid = data1 / data2 / data3
        valid[1, 0] = 15.0
        self.run_operator_test(data, operator, valid)


if __name__ == '__main__':
    tests.main()
