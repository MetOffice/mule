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


# An exception class to use when raising validation errors
class ValidateError(ValueError):
    def __init__(self, message):
        message = "LBCFile failed to validate: " + message
        super(ValidateError, self).__init__(message)


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

    def validate(self):
        """
        LBCFile validation method, ensures that certain quantities are the
        expected sizes and different header quantities are self-consistent.

        """
        # File must have its dataset_type set correctly
        dt_found = self.fixed_length_header.dataset_type
        dt_valid = 5
        if dt_found != dt_valid:
            raise ValidateError(
                "Incorrect dataset_type (found {0}, should be {1})"
                .format(dt_found, dt_valid))

        # Only grid-staggerings of 3 (NewDynamics) or 6 (ENDGame) are valid
        gs_found = self.fixed_length_header.grid_staggering
        gs_valid = [3, 6]
        if gs_found not in gs_valid:
            raise ValidateError(
                "Unsupported grid_staggering (found {0}, can support one of"
                "{1})".format(gs_found, gs_valid))

        # Integer, real and level dependent constants are mandatory
        if self.integer_constants is None:
            raise ValidateError(
                "Integer constants not found")
        if self.real_constants is None:
            raise ValidateError(
                "Real constants not found")
        if self.level_dependent_constants is None:
            raise ValidateError(
                "Level dependent constants not found")

        # Length of integer constants
        ic_length = self.integer_constants.shape[0]
        ic_valid = 46
        if ic_length != ic_valid:
            raise ValidateError(
                "Incorrect number of integer constants, "
                "(found {0}, should be {1})".format(ic_length, ic_valid))

        # Length of real constants
        rc_length = self.real_constants.shape[0]
        rc_valid = 38
        if rc_length != rc_valid:
            raise ValidateError(
                "Incorrect number of real constants, "
                "(found {0}, should be {1})".format(rc_length, rc_valid))

        # Shape of level dependent constants
        ldc_shape = self.level_dependent_constants.shape
        ldc_valid = (self.integer_constants.num_p_levels + 1, 4)
        if ldc_shape != ldc_valid:
            raise ValidateError(
                "Incorrectly shaped level dependent constants based on "
                "file type and number of levels in integer_constants "
                "(found {0}, should be {1})".format(ldc_shape, ldc_valid))

        # Sizes for row and column dependent constants
        if self.row_dependent_constants is not None:
            rdc_shape = self.row_dependent_constants.shape
            # ENDGame row dependent constants have an extra point
            if self.fixed_length_header.grid_staggering == 6:
                rdc_valid = (self.integer_constants.num_rows + 1, 2)
            else:
                rdc_valid = (self.integer_constants.num_rows, 2)
            if rdc_shape != rdc_valid:
                raise ValidateError(
                    "Incorrectly shaped row dependent constants based on "
                    "file type and number of rows in integer_constants "
                    "(found {0}, should be {1})".format(rdc_shape, rdc_valid))

        if self.column_dependent_constants is not None:
            cdc_shape = self.column_dependent_constants.shape
            cdc_valid = (self.integer_constants.num_cols, 2)
            if cdc_shape != cdc_valid:
                raise ValidateError(
                    "Incorrectly shaped column dependent constants based on "
                    "file type and number of columns in integer_constants "
                    "(found {0}, should be {1})".format(cdc_shape, cdc_valid))

        # Since we don't have access to the STASHmaster (which would
        # be strictly necessary to exmaine this in full detail) we will
        # make a few assumptions when checking the grid
        for ifield, field in enumerate(self.fields):
            if field.lbrel in (2, 3):

                if (self.row_dependent_constants is not None and
                        self.column_dependent_constants is not None):
                    # Fields on a variable resolution grid should simply
                    # contain the correct number of rows/columns (actually
                    # these can be within +/- 1 of the header value to account
                    # for the different grid-offsets)
                    col_diff = np.abs(field.lbnpt -
                                      self.integer_constants.num_cols)
                    if col_diff > 1:
                        raise ValidateError(
                            "Field {0} column count inconsistent with variable"
                            " resolution grid constants".format(ifield))
                    row_diff = np.abs(field.lbrow -
                                      self.integer_constants.num_rows)
                    if row_diff > 1:
                        raise ValidateError(
                            "Field {0} row count inconsistent with variable "
                            "resolution grid constants".format(ifield))

                    # Fields on variable grids should also have these values
                    # set specifically to RMDI
                    if field.bzx != self.real_constants.real_mdi:
                        raise ValidateError(
                            "Field {0} start longitude (bzx) not RMDI "
                            "in variable resolution file".format(ifield))
                    if field.bzy != self.real_constants.real_mdi:
                        raise ValidateError(
                            "Field {0} start latitude (bzy) not RMDI "
                            "in variable resolution file".format(ifield))
                    if field.bdx != self.real_constants.real_mdi:
                        raise ValidateError(
                            "Field {0} longitude interval (bdx) not RMDI "
                            "in variable resolution file".format(ifield))
                    if field.bdy != self.real_constants.real_mdi:
                        raise ValidateError(
                            "Field {0} latitude interval (bdy) not RMDI "
                            "in variable resolution file".format(ifield))

                else:
                    # For normal fields, the easiest way to get an idea of if
                    # all grid aspects are right is to check that the field's
                    # definition of the grid extent matches the file's
                    field_end_lon = field.bzx + field.lbnpt*field.bdx
                    file_end_lon = (self.real_constants.start_lon +
                                    self.integer_constants.num_cols *
                                    self.real_constants.col_spacing)
                    lon_diff_steps = (np.abs(field_end_lon - file_end_lon) /
                                      self.real_constants.col_spacing)

                    # For the longitude the field's result must be within 1.5
                    # grid-spacings of the P grid in the header (allow an
                    # additional 1% tolerance for rounding errors)
                    if lon_diff_steps > 1.51:
                        raise ValidateError(
                            "Field {0} grid longitudes inconsistent"
                            .format(ifield))

                    field_end_lat = field.bzy + field.lbrow*field.bdy
                    file_end_lat = (self.real_constants.start_lat +
                                    self.integer_constants.num_rows *
                                    self.real_constants.row_spacing)
                    lat_diff_steps = (np.abs(field_end_lat - file_end_lat) /
                                      self.real_constants.row_spacing)

                    # Similarly for the latitudes 1.5 grid spacings with a
                    # 1% tolerance
                    if lat_diff_steps > 1.51:
                        raise ValidateError(
                            "Field {0} grid latitudes inconsistent"
                            .format(ifield))
            else:
                # If the field has an unrecognised release number
                if field.lbrel != -99:
                    raise ValidateError(
                        "Field {0} has unrecognised release number {1}"
                        .format(ifield, field.lbrel))
