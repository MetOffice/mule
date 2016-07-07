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
import warnings
from collections import defaultdict

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

    def validate(self, filename=None, warn=False):
        """
        AncilFile validation method, ensures that certain quantities are the
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
            validators.validate_dataset_type(self, (4,)))

        # Only grid-staggerings of 3 (NewDynamics) or 6 (ENDGame) are valid
        validation_errors += (
            validators.validate_grid_staggering(self, (3, 6)))

        # Integer, real and level dependent constants are mandatory and
        # have particular lengths that must be matched
        validation_errors += (
            validators.validate_integer_constants(
                self, Ancil_IntegerConstants.CREATE_DIMS[0]))

        validation_errors += (
            validators.validate_real_constants(
                self, Ancil_RealConstants.CREATE_DIMS[0]))

        # Only continue if no errors have been raised so far (the remaining
        # checks are unlikely to work without the above passing)
        if not validation_errors:

            # Level dependent constants also mandatory
            validation_errors += (
                validators.validate_level_dependent_constants(
                    self, (self.integer_constants.num_levels,
                           Ancil_LevelDependentConstants.CREATE_DIMS[1])))

            # Sizes for row dependent constants (if present)
            if self.row_dependent_constants is not None:
                dim1 = self.integer_constants.num_rows
                # ENDGame row dependent constants have an extra point
                if self.fixed_length_header.grid_staggering == 6:
                    dim1 += 1

                validation_errors += (
                    validators.validate_row_dependent_constants(
                        self, (dim1,
                               Ancil_RowDependentConstants.CREATE_DIMS[1])))

            # Sizes for column dependent constants (if present)
            if self.column_dependent_constants is not None:
                validation_errors += (
                    validators.validate_column_dependent_constants(
                        self, (self.integer_constants.num_cols,
                               Ancil_ColumnDependentConstants.CREATE_DIMS[1])))

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
