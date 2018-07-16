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
This module provides the elements specific to UM Dumps

"""
import mule
import mule.ff
import mule.validators as validators

# UM Dump integer constant names
_DUMP_INTEGER_CONSTANTS = [comp for comp in mule.ff._FF_INTEGER_CONSTANTS]
_DUMP_INTEGER_CONSTANTS.extend([
    ('stochastic_physics_flag', 29),
    ('stochastic_physics_dim1', 30),
    ('stochastic_physics_dim2', 31),
    ('stochastic_physics_seed', 32),
    ])

# When the UM is configured to output certain special types of STASH mean,
# accumulation or trajectory diagnostics, the dump saves partial versions of
# the fields - these are not intended for interaction but we need to know
# about them in case a dump is being modified in-place
_DUMP_SPECIAL_LOOKUP_HEADER = [
    ('lbpack',  21),
    ('lbegin',  29),
    ('lbnrec',  30),
    ('lbuser1', 39),
    ('lbuser2', 40),
    ('lbuser4', 42),
    ('lbuser7', 45),
    ('bacc',    51),
    ]

_DUMP_ADDITIONAL_PARAMETERS = [
    ('stochastic_physics', (slice(None), 1)),
    ]


# Overidden versions of the relevant header elements for a DumpFile which
# are different to a FieldsFile (that it inherits from)
class Dump_IntegerConstants(mule.ff.FF_IntegerConstants):
    """The integer constants component of a UM Dump."""
    HEADER_MAPPING = _DUMP_INTEGER_CONSTANTS


# Most of the dump header components are the same as for a FieldsFile, but
# give them their own namespace ("Dump" instead of "FF")
class Dump_RealConstants(mule.ff.FF_RealConstants):
    """The real constants component of a UM Dump."""
    pass


class Dump_LevelDependentConstants(mule.ff.FF_LevelDependentConstants):
    """The level dependent constants component of a UM Dump."""
    pass


class Dump_RowDependentConstants(mule.ff.FF_RowDependentConstants):
    """The row dependent constants component of a UM Dump."""
    pass


class Dump_ColumnDependentConstants(mule.ff.FF_ColumnDependentConstants):
    """The column dependent constants component of a UM Dump."""
    pass


# Dumps also make use of the Additional Parameters, so define these here
class Dump_AdditionalParameters(mule.BaseHeaderComponent2D):
    """The additional parameters component of a UM Dump."""
    HEADER_MAPPING = _DUMP_ADDITIONAL_PARAMETERS
    CREATE_DIMS = (None, 1)
    MDI = mule._REAL_MDI
    DTYPE = ">f8"


# Additional fieldclass specific to dumps
class DumpSpecialField(mule.Field):
    """
    Field which represents a "special" dump field; these fields hold the
    partially complete contents of quantities such as means, accumulations
    and trajectories.

    """
    HEADER_MAPPING = _DUMP_SPECIAL_LOOKUP_HEADER


# The DumpFile definition itself
class DumpFile(mule.ff.FieldsFile):
    """Represents a single UM Dump."""
    # The components found in the file header (after the initial fixed-length
    # header), and their types
    COMPONENTS = (
        ('integer_constants', Dump_IntegerConstants),
        ('real_constants', Dump_RealConstants),
        ('level_dependent_constants', Dump_LevelDependentConstants),
        ('row_dependent_constants', Dump_RowDependentConstants),
        ('column_dependent_constants', Dump_ColumnDependentConstants),
        ('additional_parameters', Dump_AdditionalParameters),
        ('extra_constants', mule.UnsupportedHeaderItem1D),
        ('temp_historyfile', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index1', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index2', mule.UnsupportedHeaderItem1D),
        ('compressed_field_index3', mule.UnsupportedHeaderItem1D),
        )

    # Add an additional field type, to handle special dump fields
    FIELD_CLASSES = dict(list(mule.ff.FieldsFile.FIELD_CLASSES.items()) +
                         [(mule._INTEGER_MDI, DumpSpecialField)])

    # Set accepted dataset types
    DATASET_TYPES = (1, 2)

    # Attach to the standard validation function
    validate = validators.validate_umf
