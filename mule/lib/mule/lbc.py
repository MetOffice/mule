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
This module provides a class for interacting with LBC files.

"""
from __future__ import (absolute_import, division, print_function)

import mule
import mule.ff
import mule.validators as validators
import warnings
from collections import defaultdict

import numpy as np

# LBC Files do not recognise all of the properties from a FieldsFile, and some
# of their properties are slightly different, so override the class here
_LBC_INTEGER_CONSTANTS = [
    ('num_times',              3),
    ('num_cols',               6),
    ('num_rows',               7),
    ('num_p_levels',           8),
    ('num_wet_levels',         9),
    ('num_field_types',       15),
    ('height_algorithm',      17),
    ('integer_mdi',           21),
    ('first_constant_rho',    24),
    ]

# Similarly, the level dependent constants in an LBC file have less columns
# than a FieldsFile
_LBC_LEVEL_DEPENDENT_CONSTANTS = [
    ('eta_at_theta',      (slice(None), 1)),
    ('eta_at_rho',        (slice(None), 2)),
    ('rhcrit',            (slice(None), 3)),
    ('soil_thickness',    (slice(None), 4)),
    ]


class LBC_IntegerConstants(mule.IntegerConstants):
    """The integer constants component of a UM LBC File."""
    HEADER_MAPPING = _LBC_INTEGER_CONSTANTS
    CREATE_DIMS = (46,)


class LBC_RealConstants(mule.RealConstants):
    """The real constants component of a UM LBC File."""
    HEADER_MAPPING = mule.ff._FF_REAL_CONSTANTS
    CREATE_DIMS = (38,)


class LBC_LevelDependentConstants(mule.LevelDependentConstants):
    """The level dependent constants component of a UM LBC File."""
    HEADER_MAPPING = _LBC_LEVEL_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 4)


class LBC_RowDependentConstants(mule.RowDependentConstants):
    """The row dependent constants component of a UM LBC File."""
    HEADER_MAPPING = mule.ff._FF_ROW_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 2)


class LBC_ColumnDependentConstants(mule.ColumnDependentConstants):
    """The column dependent constants component of a UM LBC File."""
    HEADER_MAPPING = mule.ff._FF_COLUMN_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 2)


# Setup the providers for the LBC file packing types
class _ReadLBCProviderUnpacked(mule.RawReadProvider):
    """A :class:`mule.RawReadProvider` which reads an unpacked field."""
    WORD_SIZE = mule._DEFAULT_WORD_SIZE

    def _data_array(self):
        field = self.source
        data_bytes = self._read_bytes()
        dtype = mule.ff._DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data = np.fromstring(data_bytes, dtype, count=field.lblrec)
        data = data.reshape(field.lbhem - 100, -1)
        return data


class _ReadLBCProviderCray32Packed(_ReadLBCProviderUnpacked):
    """
    A :class:`mule.RawReadProvider` which reads a Cray32-bit packed field.

    """
    WORD_SIZE = mule.ff._CRAY32_SIZE


# Write operators - these handle writing out of the data components
class _WriteLBCOperatorUnpacked(object):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as unpacked LBC data.

    """
    WORD_SIZE = mule._DEFAULT_WORD_SIZE

    def __init__(self, file_obj):
        self.file = file_obj

    def to_bytes(self, field):
        data = field.get_data()
        dtype = mule.ff._DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data = data.astype(dtype)
        return data.tostring(), data.size


class _WriteLBCOperatorCray32Packed(_WriteLBCOperatorUnpacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as Cray32-bit packed LBC data.

    """
    WORD_SIZE = mule.ff._CRAY32_SIZE


# Additional operators
class LBCToMaskedArrayOperator(mule.DataOperator):
    """
    A special :class:`mule.DataOperator` provided with the LBC class - this
    will transform the 1-dimensional LBC array into a masked 3-d array where
    the points in the center of the domain are missing.

    .. Note::
        In order to write this back out as an LBC it will need to additionally
        pass through the converse :class:`MaskedArrayToLBCOperator`.

    """
    def __init__(self):
        """Initialise the operator object."""
        pass

    def new_field(self, field):
        """
        Create a copy of the source field object.

        Args:
            * field:
                The :class:`mule.Field` object to attach the operator to
                when it is called.

        """
        new_field = field.copy()
        return new_field

    def transform(self, source_field, result_field):
        """
        Retrieve the data from the original :class:`mule.Field` object,
        and construct a masked 3-d data array to return.

        Args:
            * source_field:
                The :class:`mule.Field` object which contains the means
                to extract the original data.

        .. Note::
            This method should not be called directly; it will be called
            by the "get_data" method of the :class:`mule.Field` object
            this operator has been attached to.

        """
        # Basic properties
        ncols = source_field.lbnpt
        nrows = source_field.lbrow
        num_levels = source_field.lbhem - 100
        halo_code = source_field.lbuser3

        # Rim and halo widths
        rimwidth = int(halo_code // 10000)
        halo_ns = int(halo_code - rimwidth * 10000) // 100
        halo_ew = int(halo_code - rimwidth * 10000 - halo_ns * 100)

        # Sizes for the sub-regions
        size_ns = (halo_ns + rimwidth) * (halo_ew + ncols + halo_ew)
        size_ew = (halo_ew + rimwidth) * (nrows - 2 * rimwidth)
        len_x = ncols + halo_ew * 2
        len_y = nrows + halo_ns * 2

        # Start positions for each region
        north_start = 0
        east_start = north_start + size_ns
        south_start = east_start + size_ew
        west_start = south_start + size_ns

        # Shapes for the regions
        ns_region_shape = (halo_ns + rimwidth, halo_ew*2 + ncols)
        ew_region_shape = (nrows - 2*rimwidth, halo_ew + rimwidth)

        # Get the existing data and create the 3d-array (fill it with
        # mdi initially)
        data = source_field.get_data()
        mdi = source_field.bmdi
        data_3d = np.ones((num_levels, len_y, len_x))*mdi

        for z in range(0, num_levels):
            # Extract each region from the 1-d array and reshape it
            northern_region = data[z, north_start: east_start]
            northern_region = northern_region.reshape(ns_region_shape)

            eastern_region = data[z, east_start: south_start]
            eastern_region = eastern_region.reshape(ew_region_shape)

            southern_region = data[z, south_start: west_start]
            southern_region = southern_region.reshape(ns_region_shape)

            western_region = data[z, west_start:]
            western_region = western_region.reshape(ew_region_shape)

            # Place the extracted regions into the output array
            data_3d[z,
                    len_y-halo_ns-rimwidth:len_y,
                    0:ncols+halo_ew*2] = northern_region
            data_3d[z,
                    halo_ns+rimwidth:halo_ns+nrows-rimwidth,
                    len_x-halo_ew-rimwidth:len_x] = eastern_region
            data_3d[z,
                    0:rimwidth+halo_ns,
                    0:ncols+halo_ew*2] = southern_region
            data_3d[z,
                    halo_ns+rimwidth:halo_ns+nrows-rimwidth,
                    0:halo_ew+rimwidth] = western_region

        masked_array = np.ma.masked_array(data_3d, data_3d == mdi, copy=False)

        return masked_array


class MaskedArrayToLBCOperator(mule.DataOperator):
    """
    A special :class:`mule.DataOperator` provided with the LBC class - this
    will transform the masked 3-d array produced by wrapping an LBC field in
    the :class:`LBCToMaskedArrayOperator` class back into a 1-d LBC array.

    """
    def __init__(self):
        """Initialise the operator object."""
        pass

    def new_field(self, field):
        """
        Create a copy of the source field object.

        Args:
            * field:
                The :class:`mule.Field` object to attach the operator to
                when it is called.

                This object is assumed to be the result of applying the
                :class:`LBCToMaskedArrayOperator` to an LBC field.  It will
                return a field object which reverts the transformation
                provided by that operator.

        """
        new_field = field.copy()
        return new_field

    def transform(self, source_field, result_field):
        """
        Retrieve the masked 3-d array from the :class:`mule.Field` object
        and revert it to a sequential 1-d LBC array.

        Args:
            * source_field:
                The :class:`mule.Field` object which returns the masked
                3-d array.

        .. Note::
            This method should not be called directly; it will be called
            by the "get_data" method of the :class:`mule.Field` object
            this operator has been attached to.

        """
        # Basic properties
        ncols = source_field.lbnpt
        nrows = source_field.lbrow
        num_levels = source_field.lbhem - 100
        halo_code = source_field.lbuser3

        # Rim and halo widths
        rimwidth = int(halo_code // 10000)
        halo_ns = int(halo_code - rimwidth * 10000) // 100
        halo_ew = int(halo_code - rimwidth * 10000 - halo_ns * 100)

        # Sizes for the sub-regions
        size_ns = (halo_ns + rimwidth) * (halo_ew + ncols + halo_ew)
        size_ew = (halo_ew + rimwidth) * (nrows - 2 * rimwidth)

        # Start positions for each region
        north_start = 0
        east_start = north_start + size_ns
        south_start = east_start + size_ew
        west_start = south_start + size_ns

        # Indices into transformed array
        north_start_x = 0
        north_end_x = ncols + halo_ew*2 + 1
        north_start_y = nrows - rimwidth + halo_ns
        north_end_y = nrows + halo_ns*2

        east_start_x = ncols - rimwidth + halo_ew
        east_end_x = ncols + halo_ew*2
        east_start_y = rimwidth + halo_ns
        east_end_y = nrows - rimwidth + halo_ns

        south_start_x = 0
        south_end_x = ncols + halo_ew*2 + 1
        south_start_y = 0
        south_end_y = rimwidth + halo_ns

        west_start_x = 0
        west_end_x = rimwidth + halo_ew
        west_start_y = rimwidth + halo_ns
        west_end_y = nrows - rimwidth + halo_ns

        # Size for the output
        total_size = size_ns*2 + size_ew*2

        # Get the existing data and create the 1d-array
        data_3d = source_field.get_data()
        mdi = source_field.bmdi
        data = np.ones((num_levels, total_size))*mdi

        for z in range(0, num_levels):
            # Extract each region from the 3-d array
            northern_region = data_3d[z,
                                      north_start_y:north_end_y,
                                      north_start_x:north_end_x]
            eastern_region = data_3d[z,
                                     east_start_y:east_end_y,
                                     east_start_x:east_end_x]
            southern_region = data_3d[z,
                                      south_start_y:south_end_y,
                                      south_start_x:south_end_x]
            western_region = data_3d[z,
                                     west_start_y:west_end_y,
                                     west_start_x:west_end_x]

            # Place the extracted regions into the output array
            data[z, north_start: east_start] = northern_region.ravel()

            data[z, east_start: south_start] = eastern_region.ravel()

            data[z, south_start: west_start] = southern_region.ravel()

            data[z, west_start:] = western_region.ravel()

        return data


# Otherwise and LBC file is fairly similar to a FieldsFile
class LBCFile(mule.UMFile):
    """Represents a single UM LBC File."""
    # The components of the file
    COMPONENTS = (
        ('integer_constants', LBC_IntegerConstants),
        ('real_constants', LBC_RealConstants),
        ('level_dependent_constants', LBC_LevelDependentConstants),
        ('row_dependent_constants', LBC_RowDependentConstants),
        ('column_dependent_constants', LBC_ColumnDependentConstants),
        ('fields_of_constants', mule.UnsupportedHeaderItem2D),
        ('extra_constants', mule.UnsupportedHeaderItem1D),
        ('temp_historyfile', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index1', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index2', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index3', mule.UnsupportedHeaderItem1D),
        )

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _DataProvider to use for the reading, for LBC Files
    READ_PROVIDERS = {000: _ReadLBCProviderUnpacked,
                      002: _ReadLBCProviderCray32Packed}

    WRITE_OPERATORS = {000: _WriteLBCOperatorUnpacked,
                       002: _WriteLBCOperatorCray32Packed}

    # The only other difference is that LBC files do not set the data shape
    def _write_to_file(self, output_file):
        # Do exactly what the FieldsFile class does
        super(LBCFile, self)._write_to_file(output_file)

        # But clear out the data shape property (it should be set to zero for
        # LBC files) and write the fixed length header again to update this
        self.fixed_length_header.data_shape = 0
        output_file.seek(0)
        self.fixed_length_header.to_file(output_file)

    def validate(self, filename=None, warn=False):
        """
        LBCFile validation method, ensures that certain quantities are the
        expected sizes and different header quantities are self-consistent.

        Kwargs:
            * filename:
                If provided, this filename will be included in any
                validation error messages raised by this method.
            * warn:
                If True, issue a warning rather than a failure in the event
                that the object fails to validate.

        """
        # Error messages will be accumulated in this list, so that they
        # can all be issued at once (instead of stopping after the first)
        validation_errors = []

        # File must have its dataset_type set correctly
        validation_errors += (
            validators.validate_dataset_type(self, (5,)))

        # Only grid-staggerings of 3 (NewDynamics) or 6 (ENDGame) are valid
        validation_errors += (
            validators.validate_grid_staggering(self, (3, 6)))

        # Integer, real and level dependent constants are mandatory and
        # have particular lengths that must be matched
        validation_errors += (
            validators.validate_integer_constants(
                self, LBC_IntegerConstants.CREATE_DIMS[0]))

        validation_errors += (
            validators.validate_real_constants(
                self, LBC_RealConstants.CREATE_DIMS[0]))

        # Only continue if no errors have been raised so far (the remaining
        # checks are unlikely to work without the above passing)
        if not validation_errors:

            # Level dependent constants also mandatory
            validation_errors += (
                validators.validate_level_dependent_constants(
                    self, (self.integer_constants.num_p_levels + 1,
                           LBC_LevelDependentConstants.CREATE_DIMS[1])))

            # Sizes for row dependent constants (if present)
            if self.row_dependent_constants is not None:
                dim1 = self.integer_constants.num_rows
                # ENDGame row dependent constants have an extra point
                if self.fixed_length_header.grid_staggering == 6:
                    dim1 += 1

                validation_errors += (
                    validators.validate_row_dependent_constants(
                        self, (dim1,
                               LBC_RowDependentConstants.CREATE_DIMS[1])))

            # Sizes for column dependent constants (if present)
            if self.column_dependent_constants is not None:
                validation_errors += (
                    validators.validate_column_dependent_constants(
                        self, (self.integer_constants.num_cols,
                               LBC_ColumnDependentConstants.CREATE_DIMS[1])))

            # For the fields, a dictionary will be used to accumulate the
            # errors, where the keys are the error messages.  This will allow
            # us to only print each message once (with a list of fields).
            field_validation = defaultdict(list)
            for ifield, field in enumerate(self.fields):
                if field.lbrel not in (2, 3):
                    # If the field release number isn't one of the recognised
                    # values, or -99 (a missing/padding field) error
                    if field.lbrel != -99:
                        msg = "Field has unrecognised release number {0}"
                        field_validation[
                            msg.format(field.lbrel)].append(ifield)
                else:
                    if (self.row_dependent_constants is not None and
                            self.column_dependent_constants is not None):
                        # Check that the headers are set appropriately for a
                        # variable resolution field
                        for msg in (
                                validators.validate_variable_resolution_field(
                                    self, field)):
                            field_validation[msg].append(ifield)
                    else:
                        # Check that the grids are consistent - if the STASH
                        # entry is available make use of the extra information
                        for msg in validators.validate_regular_field(
                                self, field):
                            field_validation[msg].append(ifield)

            # Unpick the messages stored in the dictionary, to provide each
            # error once along with a listing of the fields affected
            for field_msg, field_indices in field_validation.items():
                msg = "Field validation failures:\n  Fields ({0})\n{1}"
                field_str = ",".join(
                    [str(ind)
                     for ind in field_indices[:min(len(field_indices), 5)]])
                if len(field_indices) > 5:
                    field_str += (
                        ", ... {0} total fields".format(len(field_indices)))
                validation_errors.append(
                    msg.format(field_str, field_msg))

        # Now either raise an exception or warning with the messages attached.
        if validation_errors:
            if warn:
                msg = ""
                if filename is not None:
                    msg = "\nFile: {0}".format(filename)
                msg += "\n" + "\n".join(validation_errors)
                warnings.warn(msg)
            else:
                raise validators.ValidateError(
                    filename, "\n".join(validation_errors))
