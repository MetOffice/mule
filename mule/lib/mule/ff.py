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
        been added via the :meth:`set_lsm_source` method.

    """
    WORD_SIZE = mule._DEFAULT_WORD_SIZE
    _LAND = True

    def __init__(self, *args, **kwargs):
        super(_ReadFFProviderLandPacked, self).__init__(*args, **kwargs)
        self._lsm_source = None

    def set_lsm_source(self, lsm_source):
        self._lsm_source = lsm_source

    def _data_array(self):
        field = self.source
        data_bytes = self._read_bytes()
        if self._lsm_source is None:
            msg = ("Land Packed Field cannot be unpacked as it "
                   "has no associated Land-Sea mask")
            raise ValueError(msg)
        dtype = _DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data_p = np.fromstring(data_bytes, dtype, count=field.lblrec)
        if self._LAND:
            mask = np.where(self._lsm_source.ravel() == 1.0)[0]
        else:
            mask = np.where(self._lsm_source.ravel() == 0.0)[0]
        if len(mask) != len(data_p):
            msg = "Number of points in mask is incompatible; {0} != {1}"
            raise ValueError(msg.format(len(mask), len(data_p)))

        rows, cols = self._lsm_source.shape

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
        been added via the :meth:`set_lsm_source` method.

    """
    _LAND = False


class _ReadFFProviderCray32LandPacked(_ReadFFProviderLandPacked):
    """
    A :class:`mule.RawReadProvider` which reads a Cray32-bit packed field
    defined only on land points.

    .. Note::
        This requires that a reference to the Land-Sea mask Field has
        been added via the :meth:`set_lsm_source` method.

    """
    WORD_SIZE = _CRAY32_SIZE


class _ReadFFProviderCray32SeaPacked(_ReadFFProviderSeaPacked):
    """
    A :class:`mule.RawReadProvider` which reads a Cray32-bit packed field
    defined only on sea points.

    .. Note::
        This requires that a reference to the Land-Sea mask Field has
        been added via the :meth:`set_lsm_source` method.

    """
    WORD_SIZE = _CRAY32_SIZE


# Write operators - these handle writing out of the data components
class _WriteFFOperatorUnpacked(object):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as unpacked FieldsFile data.

    """
    WORD_SIZE = mule._DEFAULT_WORD_SIZE

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
        # Note: the returned data size here is a little odd; WGDOS data is
        # actually 32-bit (_WGDOS_SIZE) but for historical reasons the file
        # format reports WGDOS packed fields as if they were 64-bit.
        # If there's an odd number of 32-bit words present then integer
        # division means the final 32-bit word will not be included in the
        # resulting (64-bit) data length. Therefore we add an extra
        # 32-bit word to ensure any leftover 32-bit word is included as
        # part of the final 64-bit word and not lost. If there's an even
        # number of 32-bit words this additional (unused) 32-bit word length
        # is discarded during the division.
        return data_bytes, (len(data_bytes) + _WGDOS_SIZE)//self.WORD_SIZE


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
    _LAND = True

    def __init__(self, *args, **kwargs):
        super(_WriteFFOperatorLandPacked, self).__init__(*args, **kwargs)
        self._lsm_source = None

    def set_lsm_source(self, lsm_source):
        self._lsm_source = lsm_source

    def set_lsm_source(self, lsm_source):
        self._lsm_source = lsm_source

    def to_bytes(self, field):
        data = field.get_data()
        if self._lsm_source is None:
            msg = ("Cannot land/sea pack fields on output without a valid "
                   "land-sea-mask")
            raise ValueError(msg)

        if self._LAND:
            mask = np.where(self._lsm_source.ravel() == 1.0)[0]
        else:
            mask = np.where(self._lsm_source.ravel() == 0.0)[0]

        data = data.ravel()[mask]
        dtype = _DATA_DTYPES[self.WORD_SIZE][field.lbuser1]
        data = data.astype(dtype)
        return data.tostring(), data.size


class _WriteFFOperatorSeaPacked(_WriteFFOperatorLandPacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as unpacked FieldsFiled data defiend only on sea points.

    """
    _LAND = False


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
                  ('additional_parameters', mule.UnsupportedHeaderItem2D),
                  ('extra_constants', mule.UnsupportedHeaderItem1D),
                  ('temp_historyfile', mule.UnsupportedHeaderItem1D),
                  ('compressed_field_index1', mule.UnsupportedHeaderItem1D),
                  ('compressed_field_index2', mule.UnsupportedHeaderItem1D),
                  ('compressed_field_index3', mule.UnsupportedHeaderItem1D),
                  )

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _DataProvider to use for the reading, for FieldsFiles
    READ_PROVIDERS = {"000": _ReadFFProviderUnpacked,
                      "001": _ReadFFProviderWGDOSPacked,
                      "002": _ReadFFProviderCray32Packed,
                      "120": _ReadFFProviderLandPacked,
                      "220": _ReadFFProviderSeaPacked,
                      "122": _ReadFFProviderCray32LandPacked,
                      "222": _ReadFFProviderCray32SeaPacked}

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _WriteFFOperator to use for writing, for FieldsFiles
    WRITE_OPERATORS = {"000": _WriteFFOperatorUnpacked,
                       "001": _WriteFFOperatorWGDOSPacked,
                       "002": _WriteFFOperatorCray32Packed,
                       "120": _WriteFFOperatorLandPacked,
                       "220": _WriteFFOperatorSeaPacked,
                       "122": _WriteFFOperatorCray32LandPacked,
                       "222": _WriteFFOperatorCray32SeaPacked,
                       }

    # Set accepted dataset types
    DATASET_TYPES = (3,)

    # Attach to the standard validation function
    validate = validators.validate_umf

    def _write_to_file(self, output_file):
        """Write out to an open output file."""
        # We want to extend the UMFile version of this routine to extract the
        # land-sea mask info for the relevant operators
        lsm = None
        for field in self.fields:
            if hasattr(field, "lbuser4") and field.lbuser4 == 30:
                lsm = field.get_data()
                break

        # Assuming a valid mask was found above; attach it to the operators
        if lsm is not None:
            for _, operator in self._write_operators.items():
                if hasattr(operator, "_LAND"):
                    operator.set_lsm_source(lsm)

        # Now call the usual method
        super(FieldsFile, self)._write_to_file(output_file)

    def _read_file(self, file_or_filepath):
        """Populate the class from an existing file object or file"""
        # Similarly we want to append some land-sea mask logic to this routine
        # Start by calling the usual routine
        super(FieldsFile, self)._read_file(file_or_filepath)

        # Look for the land-sea mask
        lsm = None
        for field in self.fields:
            if hasattr(field, "lbuser4") and field.lbuser4 == 30:
                lsm = field.get_data()
                break

        # If a land-sea mask was found, attach it to the relevant fields
        if lsm is not None:
            for field in self.fields:
                if hasattr(field._data_provider, "_LAND"):
                    field._data_provider.set_lsm_source(lsm)
