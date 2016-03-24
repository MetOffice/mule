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
This module provides the elements specific to UM FieldsFiles (and dumps)

"""
from __future__ import (absolute_import, division, print_function)

import mule
import mule.validators as validators
from mule.packing import wgdos_pack_field, wgdos_unpack_field

import numpy as np

# UM FieldsFile integer constant names
_FF_INTEGER_CONSTANTS = [
    ('timestep',               1),
    ('meaning_interval',       2),
    ('dumps_in_mean',          3),
    ('num_cols',               6),
    ('num_rows',               7),
    ('num_p_levels',           8),
    ('num_wet_levels',         9),
    ('num_soil_levels',       10),
    ('num_cloud_levels',      11),
    ('num_tracer_levels',     12),
    ('num_boundary_levels',   13),
    ('num_passive_tracers',   14),
    ('num_field_types',       15),
    ('n_steps_since_river',   16),
    ('height_algorithm',      17),
    ('num_radiation_vars',    18),
    ('river_row_length',      19),
    ('river_num_rows',        20),
    ('integer_mdi',           21),
    ('triffid_call_period',   22),
    ('triffid_last_step',     23),
    ('first_constant_rho',    24),
    ('num_land_points',       25),
    ('num_ozone_levels',      26),
    ('num_tracer_adv_levels', 27),
    ('num_soil_hydr_levels',  28),
    ('num_conv_levels',       34),
    ('radiation_timestep',    35),
    ('amip_flag',             36),
    ('amip_first_year',       37),
    ('amip_first_month',      38),
    ('amip_current_day',      39),
    ('ozone_current_month',   40),
    ('sh_zonal_flag',         41),
    ('sh_zonal_begin',        42),
    ('sh_zonal_period',       43),
    ('suhe_level_weight',     44),
    ('suhe_level_cutoff',     45),
    ('frictional_timescale',  46),
    ]

_FF_REAL_CONSTANTS = [
    ('col_spacing',         1),
    ('row_spacing',         2),
    ('start_lat',           3),
    ('start_lon',           4),
    ('north_pole_lat',      5),
    ('north_pole_lon',      6),
    ('atmos_year',          8),
    ('atmos_day',           9),
    ('atmos_hour',         10),
    ('atmos_minute',       11),
    ('atmos_second',       12),
    ('top_theta_height',   16),
    ('mean_diabatic_flux', 18),
    ('mass',               19),
    ('energy',             20),
    ('energy_drift',       21),
    ('real_mdi',           29),
    ]

# UM FieldsFile level/row/column dependent constants, note that the first
# dimension of the header corresponds to the number of levels/rows/columns
# respectively and the second dimension indicates the specific nature of the
# array; therefore we use "slice(None)" to represent the first index - this
# is equivalent to inserting a ":" when performing the indexing (i.e. return
# all values for that level-type)
_FF_LEVEL_DEPENDENT_CONSTANTS = [
    ('eta_at_theta',      (slice(None), 1)),
    ('eta_at_rho',        (slice(None), 2)),
    ('rhcrit',            (slice(None), 3)),
    ('soil_thickness',    (slice(None), 4)),
    ('zsea_at_theta',     (slice(None), 5)),
    ('c_at_theta',        (slice(None), 6)),
    ('zsea_at_rho',       (slice(None), 7)),
    ('c_at_rho',          (slice(None), 8)),
    ]

_FF_ROW_DEPENDENT_CONSTANTS = [
    ('phi_p', (slice(None), 1)),
    ('phi_v', (slice(None), 2)),
    ]

_FF_COLUMN_DEPENDENT_CONSTANTS = [
    ('lambda_p', (slice(None), 1)),
    ('lambda_u', (slice(None), 2)),
    ]

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

# Maps word size and then lbuser1 (i.e. the field's data type) to a dtype.
_DATA_DTYPES = {4: {1: '>f4', 2: '>i4', 3: '>i4'},
                8: {1: '>f8', 2: '>i8', 3: '>i8'}}

# Default word sizes for Cray32 and WGDOS packed fields
_CRAY32_SIZE = 4


# Overidden versions of the relevant header elements for a FieldsFile
class FF_IntegerConstants(mule.IntegerConstants):
    """The integer constants component of a UM FieldsFile."""
    HEADER_MAPPING = _FF_INTEGER_CONSTANTS
    CREATE_DIMS = (46,)


class FF_RealConstants(mule.RealConstants):
    """The real constants component of a UM FieldsFile."""
    HEADER_MAPPING = _FF_REAL_CONSTANTS
    CREATE_DIMS = (38,)


class FF_LevelDependentConstants(mule.LevelDependentConstants):
    """The level dependent constants component of a UM FieldsFile."""
    HEADER_MAPPING = _FF_LEVEL_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 8)


class FF_RowDependentConstants(mule.RowDependentConstants):
    """The row dependent constants component of a UM FieldsFile."""
    HEADER_MAPPING = _FF_ROW_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 2)


class FF_ColumnDependentConstants(mule.ColumnDependentConstants):
    """The column dependent constants component of a UM FieldsFile."""
    HEADER_MAPPING = _FF_COLUMN_DEPENDENT_CONSTANTS
    CREATE_DIMS = (None, 2)


# Read Providers
class _ReadFFProviderUnpacked(mule.RawReadProvider):
    """A :class:`mule.RawReadProvider` which reads an unpacked field."""
    WORD_SIZE = mule._DEFAULT_WORD_SIZE

    def _data_array(self):
        field = self.source
        data_bytes = self._read_bytes()
        dtype = _DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        # If the number of rows and columns aren't available read the
        # data as a simple array instead
        size_present = hasattr(field, "lbrow") and hasattr(field, "lbnpt")
        if size_present:
            count = field.lbrow*field.lbnpt
        else:
            count = field.lblrec
        data = np.fromstring(data_bytes, dtype, count=count)
        if size_present:
            data = data.reshape(field.lbrow, field.lbnpt)
        return data


class _ReadFFProviderCray32Packed(_ReadFFProviderUnpacked):
    """
    A :class:`mule.RawReadProvider` which reads a Cray32-bit packed field.

    """
    WORD_SIZE = _CRAY32_SIZE


class _ReadFFProviderWGDOSPacked(mule.RawReadProvider):
    """A :class:`mule.RawReadProvider` which reads a WGDOS packed field."""
    def _data_array(self):
        field = self.source
        data_bytes = self._read_bytes()
        data = wgdos_unpack_field(data_bytes, field.bmdi,
                                  field.lbrow, field.lbnpt)
        return data


class _ReadFFProviderLandPacked(mule.RawReadProvider):
    """
    A :class:`mule.RawReadProvider` which reads an unpacked field defined
    only on land points.

    .. Note::
        This requires that a reference to the Land-Sea mask Field has
        been set as the "lsm_source" attribute.

    """
    WORD_SIZE = mule._DEFAULT_WORD_SIZE
    _LAND = True

    def _data_array(self):
        field = self.source
        data_bytes = self._read_bytes()
        if self.lsm_source is not None:
            lsm = self.lsm_source.get_data()
        else:
            msg = ("Land Packed Field cannot be unpacked as it "
                   "has no associated Land-Sea mask")
            raise ValueError(msg)
        dtype = _DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data_p = np.fromstring(data_bytes, dtype, count=field.lblrec)
        if self._LAND:
            mask = np.where(lsm.ravel() == 1.0)[0]
        else:
            mask = np.where(lsm.ravel() == 0.0)[0]
        if len(mask) != len(data_p):
            msg = "Number of points in mask is incompatible; {0} != {1}"
            raise ValueError(msg.format(len(mask), len(data_p)))

        rows = self.lsm_source.lbrow
        cols = self.lsm_source.lbnpt

        data = np.empty((rows*cols), dtype)
        data[:] = field.bmdi
        data[mask] = data_p
        data = data.reshape(rows, cols)
        return data


class _ReadFFProviderSeaPacked(_ReadFFProviderLandPacked):
    """
    A :class:`mule.RawReadProvider` which reads an unpacked field defined
    only on sea points.

    .. Note::
        This requires that a reference to the Land-Sea mask Field has
        been set as the "lsm_source" attribute.

    """
    _LAND = False


class _ReadFFProviderCray32LandPacked(_ReadFFProviderLandPacked):
    """
    A :class:`mule.RawReadProvider` which reads a Cray32-bit packed field
    defined only on land points.

    .. Note::
        This requires that a reference to the Land-Sea mask Field has
        been set as the "lsm_source" attribute.

    """
    WORD_SIZE = _CRAY32_SIZE


class _ReadFFProviderCray32SeaPacked(_ReadFFProviderSeaPacked):
    """
    A :class:`mule.RawReadProvider` which reads a Cray32-bit packed field
    defined only on sea points.

    .. Note::
        This requires that a reference to the Land-Sea mask Field has
        been set as the "lsm_source" attribute.

    """
    WORD_SIZE = _CRAY32_SIZE


# Write operators - these handle writing out of the data components
class _WriteFFOperatorUnpacked(object):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as unpacked FieldsFile data.

    """
    WORD_SIZE = mule._DEFAULT_WORD_SIZE

    def __init__(self, file_obj):
        self.file = file_obj

    def to_bytes(self, field):
        data = field.get_data()
        dtype = _DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data = data.astype(dtype)
        return data.tostring(), data.size


class _WriteFFOperatorWGDOSPacked(_WriteFFOperatorUnpacked):
    """
    Formats the data array from a field into bytes suitable to be written
    into the output file, as WGDOS packed FieldsFile data.

    """
    WORD_SIZE = mule._DEFAULT_WORD_SIZE

    def to_bytes(self, field):
        data = field.get_data()
        # The packing library will expect the data in native byte-ordering
        # and in the appropriate format, so ensure that is the case here
        dtype = np.dtype(_DATA_DTYPES[self.WORD_SIZE][field.lbuser1])
        native_dtype = dtype.newbyteorder("=")
        if data.dtype is not native_dtype:
            data = data.astype(native_dtype)

        data_bytes = wgdos_pack_field(data, field.bmdi, int(field.bacc))
        return data_bytes, len(data_bytes)/self.WORD_SIZE


class _WriteFFOperatorCray32Packed(_WriteFFOperatorUnpacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as Cray32-bit packed FieldsFile data.

    """
    WORD_SIZE = _CRAY32_SIZE


class _WriteFFOperatorLandPacked(_WriteFFOperatorUnpacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as unpacked FieldsFile data defined only on land points.

    """
    LAND = True

    def to_bytes(self, field):
        data = field.get_data()
        if self.LAND and hasattr(self.file, "land_mask"):
            mask = self.file.land_mask
        elif hasattr(self.file, "sea_mask"):
            mask = self.file.sea_mask
        else:
            msg = ("Cannot land/sea pack fields on output without a valid "
                   "land-sea-mask")
            raise ValueError(msg)

        data = data.ravel()[mask]
        dtype = _DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data = data.astype(dtype)
        return data.tostring(), data.size


class _WriteFFOperatorSeaPacked(_WriteFFOperatorLandPacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as unpacked FieldsFiled data defiend only on sea points.

    """
    LAND = False


class _WriteFFOperatorCray32LandPacked(_WriteFFOperatorLandPacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, a Cray32-bit packed FieldsFiled data defiend only on
    land points.

    """
    WORD_SIZE = _CRAY32_SIZE


class _WriteFFOperatorCray32SeaPacked(_WriteFFOperatorSeaPacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, a Cray32-bit packed FieldsFiled data defiend only on
    sea points.

    """
    WORD_SIZE = _CRAY32_SIZE


# Additional fieldclass specific to dumps
class DumpSpecialField(mule.Field):
    """
    Field which represents a "special" dump field; these fields hold the
    partially complete contents of quantities such as means, accumulations
    and trajectories.

    """
    HEADER_MAPPING = _DUMP_SPECIAL_LOOKUP_HEADER


# The FieldsFile definition itself
class FieldsFile(mule.UMFile):
    """Represents a single UM FieldsFile."""
    # The components found in the file header (after the initial fixed-length
    # header), and their types
    COMPONENTS = (('integer_constants', FF_IntegerConstants),
                  ('real_constants', FF_RealConstants),
                  ('level_dependent_constants', FF_LevelDependentConstants),
                  ('row_dependent_constants', FF_RowDependentConstants),
                  ('column_dependent_constants', FF_ColumnDependentConstants),
                  ('fields_of_constants', mule.UnsupportedHeaderItem2D),
                  ('extra_constants', mule.UnsupportedHeaderItem1D),
                  ('temp_historyfile', mule.UnsupportedHeaderItem1D),
                  ('compressed_field_index1', mule.UnsupportedHeaderItem1D),
                  ('compressed_field_index2', mule.UnsupportedHeaderItem1D),
                  ('compressed_field_index3', mule.UnsupportedHeaderItem1D),
                  )

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _DataProvider to use for the reading, for FieldsFiles
    READ_PROVIDERS = {000: _ReadFFProviderUnpacked,
                      001: _ReadFFProviderWGDOSPacked,
                      002: _ReadFFProviderCray32Packed,
                      120: _ReadFFProviderLandPacked,
                      220: _ReadFFProviderSeaPacked,
                      122: _ReadFFProviderCray32LandPacked,
                      222: _ReadFFProviderCray32SeaPacked}

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _WriteFFOperator to use for writing, for FieldsFiles
    WRITE_OPERATORS = {000: _WriteFFOperatorUnpacked,
                       001: _WriteFFOperatorWGDOSPacked,
                       002: _WriteFFOperatorCray32Packed,
                       120: _WriteFFOperatorLandPacked,
                       220: _WriteFFOperatorSeaPacked,
                       122: _WriteFFOperatorCray32LandPacked,
                       222: _WriteFFOperatorCray32SeaPacked,
                       }

    # Add an additional field type, to handle special dump fields
    FIELD_CLASSES = dict(mule.UMFile.FIELD_CLASSES.items()
                         + [(mule._INTEGER_MDI, DumpSpecialField)])

    def validate(self, filename=None):
        """
        FieldsFile validation method, ensures that certain quantities are the
        expected sizes and different header quantities are self-consistent.

        Kwargs:
            * filename:
                If provided, this filename will be included in any
                validation error messages raised by this method.

        """
        # File must have its dataset_type set correctly
        validators.validate_dataset_type(self, (1, 2, 3), filename)

        # Only grid-staggerings of 3 (NewDynamics) or 6 (ENDGame) are valid
        validators.validate_grid_staggering(self, (3, 6), filename)

        # Integer, real and level dependent constants are mandatory and
        # have particular lengths that must be matched
        validators.validate_integer_constants(
            self, FF_IntegerConstants.CREATE_DIMS[0], filename)

        validators.validate_real_constants(
            self, FF_RealConstants.CREATE_DIMS[0], filename)

        validators.validate_level_dependent_constants(
            self, (self.integer_constants.num_p_levels + 1,
                   FF_LevelDependentConstants.CREATE_DIMS[1]), filename)

        # Sizes for row dependent constants (if present)
        if self.row_dependent_constants is not None:
            dim1 = self.integer_constants.num_rows
            # ENDGame row dependent constants have an extra point
            if self.fixed_length_header.grid_staggering == 6:
                dim1 += 1

            validators.validate_row_dependent_constants(
                self, (dim1,
                       FF_RowDependentConstants.CREATE_DIMS[1]), filename)

        # Sizes for column dependent constants (if present)
        if self.column_dependent_constants is not None:
            validators.validate_column_dependent_constants(
                self, (self.integer_constants.num_cols,
                       FF_ColumnDependentConstants.CREATE_DIMS[1]), filename)

        # Since we don't have access to the STASHmaster (which would
        # be strictly necessary to exmaine this in full detail) we will
        # make a few assumptions when checking the grid
        for ifield, field in enumerate(self.fields):
            if (self.fixed_length_header.dataset_type in (1, 2)
                    and field.lbrel == mule._INTEGER_MDI):
                # In dumps, some headers are special mean fields
                if (field.lbpack // 1000) != 2:
                    msg = ("Field {0} is special dump field but does not"
                           "have lbpack N4 == 2")
                    raise validators.ValidateError(
                        filename,
                        msg.format(ifield))

            elif field.lbrel not in (2, 3):
                # If the field release number isn't one of the recognised
                # values, or -99 (a missing/padding field) error
                if field.lbrel != -99:
                    msg = "Field {0} has unrecognised release number {1}"
                    raise validators.ValidateError(
                        filename, msg.format(ifield, field.lbrel))
            else:
                # Land packed fields shouldn't set their rows or columns
                if (field.lbpack % 100)//10 == 2:
                    if field.lbrow != 0:
                        msg = ("Field {0} rows not set to zero for land/sea "
                               "packed field")
                        raise validators.ValidateError(
                            filename, msg.format(ifield))

                    if field.lbnpt != 0:
                        msg = ("Field {0} columns not set to zero for "
                               "land/sea packed field")
                        raise validators.ValidateError(
                            filename, msg.format(ifield))

                elif (self.row_dependent_constants is not None and
                      self.column_dependent_constants is not None):
                    # Check that the headers are set appropriately
                    validators.validate_variable_resolution_field(
                        self, field, ifield, filename)
                else:
                    # Check that the grids are consistent
                    validators.validate_regular_field(
                        self, field, ifield, filename)
