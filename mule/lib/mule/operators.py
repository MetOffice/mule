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
This module provides a series of :class:`mule.DataOperator` subclasses which
aim to provide coverage of the most commonly used functionality.  Any more
complicated applications should define their own subclasses, which allows for
full control over how the operator behaves.

See the docstrings of the individual operators for details of their call
signatures and usage.

"""
from __future__ import division

import mule
import numpy as np


# Operators which act on a single field only
# ==========================================
class AddScalarOperator(mule.DataOperator):
    """Operator which adds a scalar value to all points in a single field."""
    def __init__(self, value):
        """
        Initialise the operator, this must be done before it can be applied
        to any field objects.

        Args:
            * value:
                The scalar value which should be added to every point in
                the field.

        """
        self.value = value

    def new_field(self, source_field):
        """
        Return the new field object (a simple copy of the original).

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.

        .. Note::
            Some downstream applications may expect the value of the field's
            "lbproc" header to be updated when its data is modified; it is
            your responsibility to ensure this is done if required.

        """
        return source_field.copy()

    def transform(self, source_field, new_field):
        """
        Operate on the field data, adding the scalar value to each point.

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.
            * new_field:
                The :class:`mule.Field` subclass returned by the
                :meth:`new_field` method of this object.

        .. Note::
            If the input field defines MDI in its "bdmi" header, any points
            set to this value will be omitted from the operation.

        .. Warning;
            This method should not be called directly - it will be called
            by the new field's :meth:`get_data` method.

        """
        data = source_field.get_data()
        if hasattr(source_field, "bmdi"):
            mdi = source_field.bmdi
            mask = (data != mdi)
            data_out = np.zeros(data.shape) + mdi
            data_out[mask] = data[mask] + self.value
        else:
            data_out = data + self.value
        return data_out


class ScaleFactorOperator(mule.DataOperator):
    """Operator which multiplies points in a single field by a factor."""
    def __init__(self, factor):
        """
        Initialise the operator, this must be done before it can be applied
        to any field objects.

        Args:
            * factor:
                The factor which every point in the field should be
                multiplied by.

        """
        self.factor = factor

    def new_field(self, source_field):
        """
        Return the new field object (a simple copy of the original).

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.

        .. Note::
            Some downstream applications may expect the value of the field's
            "lbproc" header to be updated when its data is modified; it is
            your responsibility to ensure this is done if required.

        """
        return source_field.copy()

    def transform(self, source_field, new_field):
        """
        Operate on the field data, multiplyting each point by the factor.

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.
            * new_field:
                The :class:`mule.Field` subclass returned by the
                :meth:`new_field` method of this object.

        .. Note::
            If the input field defines MDI in its "bdmi" header, any points
            set to this value will be omitted from the operation.

        .. Warning;
            This method should not be called directly - it will be called
            by the new field's :meth:`get_data` method.

        """
        data = source_field.get_data()
        if hasattr(source_field, "bmdi"):
            mdi = source_field.bmdi
            mask = (data != mdi)
            data_out = np.zeros(data.shape) + mdi
            data_out[mask] = data[mask]*self.factor
        else:
            data_out = data*self.factor
        return data_out


class HardLimitOperator(mule.DataOperator):
    """Operator which restricts the range of the values in a single field."""
    def __init__(self, lower_limit=None, upper_limit=None,
                 lower_fill=None, upper_fill=None):
        """
        Initialise the operator, this must be done before it can be applied
        to any field objects.

        KWargs:
            * lower_limit:
                If provided, the minimum possible allowed value for the field
                (otherwise allow any minimum value).
            * upper_limit:
                If provided, the maximum possible allowed value for the field
                (otherwise, allow any maximum value).
            * lower_fill:
                If provided, the value to replace any points in the field
                which are outside of the lower limit (otherwise, these points
                will be set to the value of the lower limit).
            * upper_fill:
                If provided, the value to replace any points in the field
                which are outside of the upper limit (otherwise, these points
                will be set to the value of the upper limit).

        .. Note::
            You must provide at least one of upper_limit or lower_limit
            otherwise the operator will not be able to do anything and
            will raise an exception.

        """
        if lower_limit is None and upper_limit is None:
            msg = "HardLimitOperator must have at least one limit provided"
            raise ValueError(msg)

        if lower_limit is not None and lower_fill is None:
            self.lower_limit = lower_limit
            self.lower_fill = lower_limit
        else:
            self.lower_limit = lower_limit
            self.lower_fill = lower_fill
        if upper_limit is not None and upper_fill is None:
            self.upper_limit = upper_limit
            self.upper_fill = upper_limit
        else:
            self.upper_limit = upper_limit
            self.upper_fill = upper_fill

    def new_field(self, source_field):
        """
        Return the new field object (a simple copy of the original).

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.

        .. Note::
            Some downstream applications may expect the value of the field's
            "lbproc" header to be updated when its data is modified; it is
            your responsibility to ensure this is done if required.

        """
        return source_field.copy()

    def transform(self, source_field, new_field):
        """
        Operate on the field data, applying the limits to the field.

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.
            * new_field:
                The :class:`mule.Field` subclass returned by the
                :meth:`new_field` method of this object.

        .. Note::
            If the input field defines MDI in its "bdmi" header, any points
            set to this value will be omitted from the operation.

        .. Warning;
            This method should not be called directly - it will be called
            by the new field's :meth:`get_data` method.

        """
        data = source_field.get_data()
        data_out = data.copy()
        if self.lower_limit is not None:
            data_out[(data < self.lower_limit)] = self.lower_fill
        if self.upper_limit is not None:
            data_out[(data > self.upper_limit)] = self.upper_fill
        if hasattr(source_field, "bmdi"):
            mdi = source_field.bmdi
            mask = (data == mdi)
            data_out[mask] = mdi
        return data_out


class ValueExchangeOperator(mule.DataOperator):
    """Operator which sets points with a particular value to a new value."""
    def __init__(self, target_value, new_value):
        """
        Initialise the operator, this must be done before it can be applied
        to any field objects.

        Args:
            * target_value:
                The value of the points which should be replaced.
            * new_value:
                The value to use to replace any selected points.

        """
        self.target_value = target_value
        self.new_value = new_value

    def new_field(self, source_field):
        """
        Return the new field object (a simple copy of the original).

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.

        .. Note::
            Some downstream applications may expect the value of the field's
            "lbproc" header to be updated when its data is modified; it is
            your responsibility to ensure this is done if required.

        """
        return source_field.copy()

    def transform(self, source_field, new_field):
        """
        Operate on the field data, swapping the values of the desired points.

        Args:
            * source_field:
                The :class:`mule.Field` subclass containing the input
                field headers and data.
            * new_field:
                The :class:`mule.Field` subclass returned by the
                :meth:`new_field` method of this object.

        .. Note::
            If the input field defines MDI in its "bdmi" header, any points
            set to this value will be omitted from the operation.

        .. Warning;
            This method should not be called directly - it will be called
            by the new field's :meth:`get_data` method.

        """
        data = source_field.get_data()
        data[(data == self.target_value)] = self.new_value
        return data


# Operators which act on multiple fields
# ======================================
class _MultiFieldOperatorBase(mule.DataOperator):
    """Base class operator which combines fields using a simple operation."""
    def __init__(self, preserve_mdi=True, mdi_val=None):
        """
        Initialise the operator, this must be done before it can be applied
        to any field objects.

        KWargs:
            * preserve_mdi:
                If True (default), the presence of an MDI value at a point
                in *any* one of the fields used in the combination will
                result in that point being set to MDI in the output field.
            * mdi_val:
                The value to interpret as MDI in the fields; if not provided
                this will be the "bmdi" value of the first field provided to
                the operator.

        """
        self.preserve_mdi = preserve_mdi
        self.mdi_val = mdi_val

    def new_field(self, source_field_list):
        """
        Return the new field object (a simple copy of the first field).

        Args:
            * source_field_list:
                A list containing at least 2 :class:`mule.Field` subclass
                objects with the input field headers and data.

        .. Note::
            Some downstream applications may expect the value of the field's
            "lbproc" header to be updated when its data is modified; it is
            your responsibility to ensure this is done if required.

        """
        return source_field_list[0].copy()

    def _operation(self, data1, data2):
        """The operation used to combine each pair of fields together."""
        msg = "Base Multi-field operator should not be used directly"
        raise ValueError(msg)

    def transform(self, source_field_list, new_field):
        """
        Operate on the data in the list of fields, combining them together
        using the chosen operation.

        Args:
            * source_field_list:
                A list containing at least 2 :class:`mule.Field` subclass
                objects with the input field headers and data.
            * new_field:
                The :class:`mule.Field` subclass returned by the
                :meth:`new_field` method of this object.

        .. Note::
           MDI values will be treated differently depending on how the
           operator was initialised (see the docstrings for more details)

        .. Warning;
            This method should not be called directly - it will be called
            by the new field's :meth:`get_data` method.

        """
        # Get the first field object and its data
        field1 = source_field_list[0]
        data_out = field1.get_data()
        # If mdi is to be ignored, create a boolean mask array from the
        # first field containing its mdi points
        if self.preserve_mdi:
            if self.mdi_val is None:
                self.mdi_val = field1.bmdi
            mask = (data_out == self.mdi_val)
        # Now iterate through the other fields in the list
        for field in source_field_list[1:]:
            # Update the field data with whatever operation is needed
            data = field.get_data()
            data_out = self._operation(data_out, data)
            # If we are handling mdi; update the mask to include
            # any points not already flagged
            if self.preserve_mdi:
                mask = mask + (data == self.mdi_val)
        # At this point the mask will contain all points which
        # contained mdi in any one of the fields in the sum, so
        # the values can be reset to mdi here
        if self.preserve_mdi:
            data_out[mask] = self.mdi_val
        return data_out


class AddFieldsOperator(_MultiFieldOperatorBase):
    """Operator which adds multiple fields."""
    def _operation(self, data1, data2):
        return data1 + data2


class SubtractFieldsOperator(_MultiFieldOperatorBase):
    """Operator which subtracts multiple fields."""
    def _operation(self, data1, data2):
        return data1 - data2


class MultiplyFieldsOperator(_MultiFieldOperatorBase):
    """Operator which multiplies multiple fields."""
    def _operation(self, data1, data2):
        return data1 * data2


class DivideFieldsOperator(_MultiFieldOperatorBase):
    """Operator which divides multiple fields."""
    def _operation(self, data1, data2):
        return data1 / data2
