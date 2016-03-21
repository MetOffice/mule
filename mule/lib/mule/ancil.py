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
import mule.validators as validators

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

    def validate(self, filename=None):
        """
        AncilFile validation method, ensures that certain quantities are the
        expected sizes and different header quantities are self-consistent.

        Kwargs:
            * filename:
                If provided, this filename will be included in any
                validation error messages raised by this method.

        """
        # File must have its dataset_type set correctly
        validators.validate_dataset_type(self, (4,), filename)

        # Only grid-staggerings of 3 (NewDynamics) or 6 (ENDGame) are valid
        validators.validate_grid_staggering(self, (3, 6), filename)

        # Integer, real and level dependent constants are mandatory and
        # have particular lengths that must be matched
        validators.validate_integer_constants(
            self, Ancil_IntegerConstants.CREATE_DIMS[0], filename)

        validators.validate_real_constants(
            self, Ancil_RealConstants.CREATE_DIMS[0], filename)

        validators.validate_level_dependent_constants(
            self, (self.integer_constants.num_levels,
                   Ancil_LevelDependentConstants.CREATE_DIMS[1]), filename)

        # Sizes for row dependent constants (if present)
        if self.row_dependent_constants is not None:
            dim1 = self.integer_constants.num_rows
            # ENDGame row dependent constants have an extra point
            if self.fixed_length_header.grid_staggering == 6:
                dim1 += 1

            validators.validate_row_dependent_constants(
                self, (dim1,
                       Ancil_RowDependentConstants.CREATE_DIMS[1]), filename)

        # Sizes for column dependent constants (if present)
        if self.column_dependent_constants is not None:
            validators.validate_column_dependent_constants(
                self, (
                    self.integer_constants.num_cols,
                    Ancil_ColumnDependentConstants.CREATE_DIMS[1]), filename)

        # Since we don't have access to the STASHmaster (which would
        # be strictly necessary to exmaine this in full detail) we will
        # make a few assumptions when checking the grid
        for ifield, field in enumerate(self.fields):
            if field.lbrel not in (2, 3):
                # If the field release number isn't one of the recognised
                # values, or -99 (a missing/padding field) error
                if field.lbrel != -99:
                    msg = "Field {0} has unrecognised release number {1}"
                    raise validators.ValidateError(
                        filename, msg.format(ifield, field.lbrel))
            else:
                if (self.row_dependent_constants is not None and
                        self.column_dependent_constants is not None):
                    # Check that the headers are set appropriately
                    validators.validate_variable_resolution_field(
                        self, field, ifield, filename)

                else:
                    # Check that the grids are consistent
                    validators.validate_regular_field(
                        self, field, ifield, filename)
