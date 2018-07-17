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
import mule.validators as validators

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

# UM Ancil file row dependent constant names
_ANCIL_ROW_DEPENDENT_CONSTANTS = [
    ('phi_p', (slice(None), 1)),
    ]

# UM Ancil file column dependent constant names
_ANCIL_COLUMN_DEPENDENT_CONSTANTS = [
    ('lambda_p', (slice(None), 1)),
    ]


class Ancil_IntegerConstants(mule.IntegerConstants):
    """The integer constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_INTEGER_CONSTANTS
    CREATE_DIMS = (15,)


class Ancil_RealConstants(mule.RealConstants):
    """The real constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_REAL_CONSTANTS
    CREATE_DIMS = (6,)


class Ancil_RowDependentConstants(mule.RowDependentConstants):
    """The row dependent constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_ROW_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 1)


class Ancil_ColumnDependentConstants(mule.ColumnDependentConstants):
    """The column dependent constants component of a UM Ancillary File."""
    HEADER_MAPPING = _ANCIL_COLUMN_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 1)


# Define the ancil file class itself - it inherits from a FieldsFile rather
# than a UMFile, because it inherits many parts from the FieldsFile class
class AncilFile(mule.FieldsFile):
    """Represents a single UM Ancillary File."""
    # The components of the file
    COMPONENTS = (
        ('integer_constants', Ancil_IntegerConstants),
        ('real_constants', Ancil_RealConstants),
        ('level_dependent_constants', mule.UnsupportedHeaderItem2D),
        ('row_dependent_constants', Ancil_RowDependentConstants),
        ('column_dependent_constants', Ancil_ColumnDependentConstants),
        ('additional_parameters', mule.UnsupportedHeaderItem2D),
        ('extra_constants', mule.UnsupportedHeaderItem1D),
        ('temp_historyfile', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index1', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index2', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index3', mule.UnsupportedHeaderItem1D),
        )

    # Set the field classes back to the standard set (only FieldsFiles need
    # the special dump fields)
    FIELD_CLASSES = mule.UMFile.FIELD_CLASSES

    # Set accepted dataset types
    DATASET_TYPES = (4,)

    # Attach to the standard validation function
    validate = validators.validate_umf
