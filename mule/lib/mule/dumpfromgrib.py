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
This module provides the elements for the special class of Dumps which are
created from a GRIB file. (For example these may represent the RECONTMP file
generated in GRIB -> UM Dump reconfiguration.)

These are similar to regular Dumps, but require different validation because
having originated on GRIB grids, they contain a grid_staggering of 1
(Arakawa A grid).

"""
import mule
import mule.dump
import mule.validators


def validate_umf_dumpfromgrib(umf, filename=None, warn=False):
    """
    Wrapper for the main validation method, to additionally set the
    GridArakawaA Kwarg

    Kwargs:
        * filename:
            If provided, this filename will be included in any
            validation error messages raised by this method.
        * warn:
            If True, issue a warning rather than a failure in the event
            that the object fails to validate.

    """

    mule.validators.validate_umf(umf, filename, warn, GridArakawaA=True)


# The DumpFile definition itself
class DumpFromGribFile(mule.dump.DumpFile):
    """Represents a single UM Dump from GRIB reconfiguration."""

    # Most attributes should be inherited from the DumpFile class
    COMPONENTS = mule.dump.DumpFile.COMPONENTS
    FIELD_CLASSES = mule.dump.DumpFile.FIELD_CLASSES

    # Only instantaneous dumps are valid in this context.
    DATASET_TYPES = (1,)

    # Attach to the standard validation function
    validate = validate_umf_dumpfromgrib
