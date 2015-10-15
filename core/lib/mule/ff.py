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
import numpy as np
from mule.packing import wgdos_pack_field, wgdos_unpack_field

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

# Maps word size and then lbuser1 (i.e. the field's data type) to a dtype.
_DATA_DTYPES = {4: {1: '>f4', 2: '>i4', 3: '>i4'},
                8: {1: '>f8', 2: '>i8', 3: '>i8'}}

# Default word sizes for Cray32 and WGDOS packed fields
_CRAY32_SIZE = 4
_WGDOS_SIZE = 4


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

    @property
    def data(self):
        field = self.source
        data_bytes = self._read_bytes()
        dtype = _DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data = np.fromstring(data_bytes, dtype,
                             count=field.lbrow*field.lbnpt)
        data = data.reshape(field.lbrow, field.lbnpt)
        return data


class _ReadFFProviderCray32Packed(_ReadFFProviderUnpacked):
    """
    A :class:`mule.RawReadProvider` which reads a Cray32-bit packed field.

    """
    WORD_SIZE = _CRAY32_SIZE


class _ReadFFProviderWGDOSPacked(mule.RawReadProvider):
    """A :class:`mule.RawReadProvider` which reads a WGDOS packed field."""
    @property
    def data(self):
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

    @property
    def data(self):
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
    WORD_SIZE = _WGDOS_SIZE

    def to_bytes(self, field):
        data = field.get_data()
        data_bytes = wgdos_pack_field(data, field.bmdi, int(field.bacc))
        return data_bytes, len(data_bytes)/(2*self.WORD_SIZE)


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


# An exception class to use when raising validation errors
class ValidateError(ValueError):
    def __init__(self, message):
        message = "FieldsFile failed to validate: " + message
        super(ValidateError, self).__init__(message)


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

    def validate(self):
        """
        FieldsFile validation method, ensures that certain quantities are the
        expected sizes and different header quantities are self-consistent.

        """
        # File must have its dataset_type set correctly
        dt_found = self.fixed_length_header.dataset_type
        dt_valid = [1, 2, 3]
        if dt_found not in dt_valid:
            raise ValidateError(
                "Incorrect dataset_type (found {0}, should be one of {1})"
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
        ldc_valid = (self.integer_constants.num_p_levels + 1, 8)
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
            if field.lbrel != -99:

                # Land packed fields shouldn't set their rows or columns
                if (field.lbpack % 100)//10 == 2:
                    if field.lbrow != 0:
                        raise ValidateError(
                            "Field {0} rows not set to zero for land/sea "
                            "packed field".format(ifield))
                    if field.lbnpt != 0:
                        raise ValidateError(
                            "Field {0} columns not set to zero for "
                            "land/sea packed field".format(ifield))

                elif (self.row_dependent_constants is not None and
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
                    lon_diff = np.abs(field_end_lon - file_end_lon)

                    # For the longitude the field's result must be within 1
                    # grid-spacing of the P grid in the header
                    if lon_diff > self.real_constants.col_spacing:
                        raise ValidateError(
                            "Field {0} grid longitudes inconsistent"
                            .format(ifield))

                    field_end_lat = field.bzy + field.lbrow*field.bdy
                    file_end_lat = (self.real_constants.start_lat +
                                    self.integer_constants.num_rows *
                                    self.real_constants.row_spacing)
                    lat_diff = np.abs(field_end_lat - file_end_lat)

                    # For the latitudes allow an extra half a spacing
                    if lat_diff > 1.5*self.real_constants.row_spacing:
                        raise ValidateError(
                            "Field {0} grid latitudes inconsistent"
                            .format(ifield))
