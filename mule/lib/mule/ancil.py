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
This module provides a class for interacting with Ancillary files.

"""
from __future__ import (absolute_import, division, print_function)

import mule
import mule.ff
import numpy as np

# UM Ancil file integer constant names
_ANCIL_INTEGER_CONSTANTS = [
    ('num_times',              3),
    ('num_cols',               6),
    ('num_rows',               7),
    ('num_levels',             8),
    ('num_field_types',       15),
    ]

# UM Ancil file real constant names
_ANCIL_REAL_CONSTANTS = [
    ('col_spacing',         1),
    ('row_spacing',         2),
    ('start_lat',           3),
    ('start_lon',           4),
    ('north_pole_lat',      5),
    ('north_pole_lon',      6),
    ]

# UM Ancil file level dependent constant names
_ANCIL_LEVEL_DEPENDENT_CONSTANTS = [
    ('eta_at_theta',      (slice(None), 1)),
    ('eta_at_rho',        (slice(None), 2)),
    ('rhcrit',            (slice(None), 3)),
    ('soil_thickness',    (slice(None), 4)),
    ]

# UM Ancil file row dependent constant names
_ANCIL_ROW_DEPENDENT_CONSTANTS = [
    ('phi_p', (slice(None), 1)),
    ('phi_v', (slice(None), 2)),
    ]

# UM Ancil file column dependent constant names
_ANCIL_COLUMN_DEPENDENT_CONSTANTS = [
    ('lambda_p', (slice(None), 1)),
    ('lambda_u', (slice(None), 2)),
    ]


class Ancil_IntegerConstants(mule.IntegerConstants):
    """The integer constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_INTEGER_CONSTANTS
    CREATE_DIMS = (15,)


class Ancil_RealConstants(mule.RealConstants):
    """The real constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_REAL_CONSTANTS
    CREATE_DIMS = (6,)


class Ancil_LevelDependentConstants(mule.LevelDependentConstants):
    """The level dependent constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_LEVEL_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 4)


class Ancil_RowDependentConstants(mule.RowDependentConstants):
    """The row dependent constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_ROW_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 2)


class Ancil_ColumnDependentConstants(mule.ColumnDependentConstants):
    """The column dependent constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_COLUMN_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 2)


# An exception class to use when raising validation errors
class ValidateError(ValueError):
    def __init__(self, message):
        message = "AncilFile failed to validate: " + message
        super(ValidateError, self).__init__(message)


# Define the ancil file class itself
class AncilFile(mule.UMFile):
    """Represents a single UM Ancillary File."""
    # The components of the file
    COMPONENTS = (
        ('integer_constants', Ancil_IntegerConstants),
        ('real_constants', Ancil_RealConstants),
        ('level_dependent_constants', Ancil_LevelDependentConstants),
        ('row_dependent_constants', Ancil_RowDependentConstants),
        ('column_dependent_constants', Ancil_ColumnDependentConstants),
        ('fields_of_constants', mule.UnsupportedHeaderItem2D),
        ('extra_constants', mule.UnsupportedHeaderItem1D),
        ('temp_historyfile', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index1', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index2', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index3', mule.UnsupportedHeaderItem1D),
        )

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _DataProvider to use for the reading.  Note that ancillary
    # files simply support the exact same read providers as FieldsFiles
    READ_PROVIDERS = mule.ff.FieldsFile.READ_PROVIDERS

    # And it also supports the same write operators
    WRITE_OPERATORS = mule.ff.FieldsFile.WRITE_OPERATORS

    def validate(self):
        """
        AncilFile validation method, ensures that certain quantities are the
        expected sizes and different header quantities are self-consistent.

        """
        # File must have its dataset_type set correctly
        dt_found = self.fixed_length_header.dataset_type
        dt_valid = 4
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
        ic_valid = Ancil_IntegerConstants.CREATE_DIMS[0]
        if ic_length != ic_valid:
            raise ValidateError(
                "Incorrect number of integer constants, "
                "(found {0}, should be {1})".format(ic_length, ic_valid))

        # Length of real constants
        rc_length = self.real_constants.shape[0]
        rc_valid = Ancil_RealConstants.CREATE_DIMS[0]
        if rc_length != rc_valid:
            raise ValidateError(
                "Incorrect number of real constants, "
                "(found {0}, should be {1})".format(rc_length, rc_valid))

        # Shape of level dependent constants
        ldc_shape = self.level_dependent_constants.shape
        ldc_valid = (self.integer_constants.num_levels,
                     Ancil_LevelDependentConstants.CREATE_DIMS[1])
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
                rdc_valid = (self.integer_constants.num_rows + 1,
                             Ancil_RowDependentConstants.CREATE_DIMS[1])
            else:
                rdc_valid = (self.integer_constants.num_rows,
                             Ancil_RowDependentConstants.CREATE_DIMS[1])
            if rdc_shape != rdc_valid:
                raise ValidateError(
                    "Incorrectly shaped row dependent constants based on "
                    "file type and number of rows in integer_constants "
                    "(found {0}, should be {1})".format(rdc_shape, rdc_valid))

        if self.column_dependent_constants is not None:
            cdc_shape = self.column_dependent_constants.shape
            cdc_valid = (self.integer_constants.num_cols,
                         Ancil_ColumnDependentConstants.CREATE_DIMS[1])
            if cdc_shape != cdc_valid:
                raise ValidateError(
                    "Incorrectly shaped column dependent constants based on "
                    "file type and number of columns in integer_constants "
                    "(found {0}, should be {1})".format(cdc_shape, cdc_valid))

        # Since we don't have access to the STASHmaster (which would
        # be strictly necessary to exmaine this in full detail) we will
        # make a few assumptions when checking the grid
        for ifield, field in enumerate(self.fields):
            if field.lbrel not in (2, 3):
                # If the field release number isn't one of the recognised
                # values, or -99 (a missing/padding field) error
                if field.lbrel != -99:
                    raise ValidateError(
                        "Field {0} has unrecognised release number {1}"
                        .format(ifield, field.lbrel))
            else:
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
