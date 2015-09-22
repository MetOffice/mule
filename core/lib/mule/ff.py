#!/usr/bin/env python
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
This module provides the elements specific to FieldsFiles (and dumps)

"""
from __future__ import (absolute_import, division, print_function)

from mule import (IntegerConstants, RealConstants, LevelDependentConstants,
                  RowDependentConstants, ColumnDependentConstants, UMFile,
                  _RawReadProvider, DEFAULT_WORD_SIZE)
import numpy as np

# The packing module will select and return a suitable set of packing methods
from mule.packing import wgdos_pack_field, wgdos_unpack_field

# UM FieldsFile integer constant names
_FF_INTEGER_CONSTANTS = [
    ('timestep',              1  ),
    ('meaning_interval',      2  ),
    ('dumps_in_mean',         3  ),
    ('num_cols',              6  ),
    ('num_rows',              7  ),
    ('num_p_levels',          8  ),
    ('num_wet_levels',        9  ),
    ('num_soil_levels',       10 ),
    ('num_cloud_levels',      11 ),
    ('num_tracer_levels',     12 ),
    ('num_boundary_levels',   13 ),
    ('num_passive_tracers',   14 ),
    ('num_field_types',       15 ),
    ('n_steps_since_river',   16 ),
    ('height_algorithm',      17 ),
    ('num_radiation_vars',    18 ),
    ('river_row_length',      19 ),
    ('river_num_rows',        20 ),
    ('integer_mdi',           21 ),
    ('triffid_call_period',   22 ),
    ('triffid_last_step',     23 ),
    ('first_constant_rho',    24 ),
    ('num_land_points',       25 ),
    ('num_ozone_levels',      26 ),
    ('num_tracer_adv_levels', 27 ),
    ('num_soil_hydr_levels',  28 ),
    ('num_conv_levels',       34 ),
    ('radiation_timestep',    35 ),
    ('amip_flag',             36 ),
    ('amip_first_year',       37 ),
    ('amip_first_month',      38 ),
    ('amip_current_day',      39 ),
    ('ozone_current_month',   40 ),
    ('sh_zonal_flag',         41 ),
    ('sh_zonal_begin',        42 ),
    ('sh_zonal_period',       43 ),
    ('suhe_level_weight',     44 ),
    ('suhe_level_cutoff',     45 ),
    ('frictional_timescale',  46 ),
    ]

_FF_REAL_CONSTANTS = [
    ('col_spacing',        1  ),
    ('row_spacing',        2  ),
    ('start_lat',          3  ),
    ('start_lon',          4  ),
    ('north_pole_lat',     5  ),
    ('north_pole_lon',     6  ),
    ('atmos_year',         8  ),
    ('atmos_day',          9  ),
    ('atmos_hour',         10 ),
    ('atmos_minute',       11 ),
    ('atmos_second',       12 ),
    ('top_theta_height',   16 ),
    ('mean_diabatic_flux', 18 ),
    ('mass',               19 ),
    ('energy',             20 ),
    ('energy_drift',       21 ),
    ('real_mdi',           29 ),
    ]

# UM FieldsFile level/row/column dependent constants, note that the first
# dimension of the header corresponds to the number of levels/rows/columns
# respectively and the second dimension indicates the specific nature of the
# array; therefore we use "slice(None)" to represent the first index - this
# is equivalent to inserting a ":" when performing the indexing (i.e. return
# all values for that level-type)
_FF_LEVEL_DEPENDENT_CONSTANTS = [
    ('eta_at_theta',      (slice(None), 1) ),
    ('eta_at_rho',        (slice(None), 2) ),
    ('rhcrit',            (slice(None), 3) ),
    ('soil_thickness',    (slice(None), 4) ),
    ('zsea_at_theta',     (slice(None), 5) ),
    ('c_at_theta',        (slice(None), 6) ),
    ('zsea_at_rho',       (slice(None), 7) ),
    ('c_at_rho',          (slice(None), 8) ),
    ]

_FF_ROW_DEPENDENT_CONSTANTS = [
    ('phi_p', (slice(None), 1) ),
    ('phi_v', (slice(None), 2) ),
    ]

_FF_COLUMN_DEPENDENT_CONSTANTS = [
    ('lambda_p', (slice(None), 1) ),
    ('lambda_u', (slice(None), 2) ),
    ]

# Maps word size and then lbuser1 (i.e. the field's data type) to a dtype.
_DATA_DTYPES = {4: {1: '>f4', 2: '>i4', 3: '>i4'},
                8: {1: '>f8', 2: '>i8', 3: '>i8'}}

# Default word sizes for Cray32 and WGDOS packed fields
_CRAY32_SIZE = 4
_WGDOS_SIZE = 4

# Overidden versions of the relevant header elements for a FieldsFile
class FF_IntegerConstants(IntegerConstants):
    HEADER_MAPPING = _FF_INTEGER_CONSTANTS

class FF_RealConstants(RealConstants):
    HEADER_MAPPING = _FF_REAL_CONSTANTS

class FF_LevelDependentConstants(LevelDependentConstants):
    HEADER_MAPPING = _FF_LEVEL_DEPENDENT_CONSTANTS

class FF_RowDependentConstants(RowDependentConstants):
    HEADER_MAPPING = _FF_ROW_DEPENDENT_CONSTANTS    

class FF_ColumnDependentConstants(ColumnDependentConstants):
    HEADER_MAPPING = _FF_COLUMN_DEPENDENT_CONSTANTS

# Read Providers
class _ReadFFProviderUnpacked(_RawReadProvider):
    """
    A _DataProvider which extends the _RawReadProvider to read a FieldsFile
    which has not been packed.
    
    """    
    @property
    def data(self):
        field = self.source
        data_bytes = self._read_bytes()
        dtype = _DATA_DTYPES[self.word_size][field.lbuser1]
        data = np.fromstring(data_bytes, dtype,
                             count=field.lbrow*field.lbnpt)
        data = data.reshape(field.lbrow, field.lbnpt)
        return data

class _ReadFFProviderCray32Packed(_ReadFFProviderUnpacked):
    """
    A _DataProvider which reads and then unpacks a FieldsFile which has been
    packed using the Cray 32-bit packing method - note that this is similar
    to the unpacked case but with a different word size.
    
    """
    @property
    def data(self):
        self.word_size = _CRAY32_SIZE
        return super(_ReadFFProviderCray32Packed, self).data

class _ReadFFProviderWGDOSPacked(_RawReadProvider):
    """
    A _DataProvider which extends the _RawReadProvider to read and then unpack
    a FieldsFile which has been packed using the WGDOS packing method.
    
    """    
    @property
    def data(self):
        field = self.source
        data_bytes = self._read_bytes()
        data = wgdos_unpack_field(data_bytes, field.bmdi,
                                  field.lbrow, field.lbnpt)
        return data

class _ReadFFProviderLandPacked(_RawReadProvider):
    """
    A _DataProvider which extends the _RawReadProvider to read and then unpack
    a FieldsFile which has been land-packed.  Note that this requires that a
    reference to the Land-Sea mask Field has been set as the "lsm_source".
    
    """
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
        dtype = _DATA_DTYPES[self.word_size][field.lbuser1]
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
    A _DataProvider which behaves the same as the LandPacked provider but the
    packing takes place over sea points instead of land points.
    
    """
    _LAND= False
    
class _ReadFFProviderCray32LandPacked(_ReadFFProviderLandPacked):
    """
    A _DataProvider which reads and then unpacks a Field which has been packed
    using the Cray 32-bit packing method with land-packing - note that this is
    similar to the LandPacked case but with a different word size.
    
    """
    @property
    def data(self):
        self.word_size = _CRAY32_SIZE
        return super(_ReadFFProviderCray32LandPacked, self).data

class _ReadFFProviderCray32SeaPacked(_ReadFFProviderSeaPacked):
    """
    A _DataProvider which reads and then unpacks a Field which has been packed
    using the Cray 32-bit packing method with sea-packing - note that this is
    similar to the SeaPacked case but with a different word size.
    
    """
    @property
    def data(self):
        self.word_size = _CRAY32_SIZE
        return super(_ReadFFProviderCray32SeaPacked, self).data

# Write operators - these handle writing out of the data components
class _WriteFFOperatorUnpacked(object):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as unpacked FieldsFile data
    """    
    WORD_SIZE = DEFAULT_WORD_SIZE
    def __init__(self, file_obj):
        self.file = file_obj
        
    def to_bytes(self, field):
        data = field.get_data()
        kind = {1: 'f', 2: 'i', 3: 'i'}.get(field.lbuser1, data.dtype.kind)        
        data = data.astype('>{0}{1}'.format(kind, self.WORD_SIZE))
        return data.tostring(), data.size

class _WriteFFOperatorWGDOSPacked(_WriteFFOperatorUnpacked):
    """
    Formats the data array from a field into bytes suitable to be written
    into the output file, as WGDOS packed FieldsFile data
    """
    WORD_SIZE = _WGDOS_SIZE
    def to_bytes(self, field):
        data = field.get_data()
        data_bytes = wgdos_pack_field(data, field.bmdi, int(field.bacc))
        return data_bytes, len(data_bytes)/(2*self.WORD_SIZE)

class _WriteFFOperatorCray32Packed(_WriteFFOperatorUnpacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as Cray32 packed FieldsFile data
    """    
    WORD_SIZE = _CRAY32_SIZE

class _WriteFFOperatorLandPacked(_WriteFFOperatorUnpacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as Land packed FieldsFile data
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
        kind = {1: 'f', 2: 'i', 3: 'i'}.get(field.lbuser1, data.dtype.kind)        
        data = data.astype('>{0}{1}'.format(kind, self.WORD_SIZE))
        return data.tostring(), data.size

class _WriteFFOperatorSeaPacked(_WriteFFOperatorLandPacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as Sea packed FieldsFile data
    """  
    LAND = False

class _WriteFFOperatorCray32LandPacked(_WriteFFOperatorLandPacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as Cray32 Land packed FieldsFile data
    """
    WORD_SIZE = _CRAY32_SIZE
    
class _WriteFFOperatorCray32SeaPacked(_WriteFFOperatorSeaPacked):
    """
    Formats the data array from a field into bytes suitable to be written into
    the output file, as Cray32 Land packed FieldsFile data
    """
    WORD_SIZE = _CRAY32_SIZE

# The FieldsFile definition itself
class FieldsFile(UMFile):
    """
    Representes a single UM FieldsFile
    
    """
    # The dataset types for FieldsFiles + Dumps
    _DATASET_TYPES = [1,2,3]

    # The components found in the file header (after the initial fixed-length
    # header), and their types
    _COMPONENTS = (('integer_constants', FF_IntegerConstants),
                   ('real_constants', FF_RealConstants),
                   ('level_dependent_constants', FF_LevelDependentConstants),
                   ('row_dependent_constants', FF_RowDependentConstants),
                   ('column_dependent_constants', FF_ColumnDependentConstants))

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _DataProvider to use for the reading, for FieldsFiles
    _READ_PROVIDERS = {000: _ReadFFProviderUnpacked,
                       001: _ReadFFProviderWGDOSPacked,
                       002: _ReadFFProviderCray32Packed,
                       120: _ReadFFProviderLandPacked,
                       220: _ReadFFProviderSeaPacked,
                       122: _ReadFFProviderCray32LandPacked,
                       222: _ReadFFProviderCray32SeaPacked}

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _WriteFFOperator to use for writing, for FieldsFiles
    _WRITE_OPERATORS = {000: _WriteFFOperatorUnpacked,
                        001: _WriteFFOperatorWGDOSPacked,
                        002: _WriteFFOperatorCray32Packed,
                        120: _WriteFFOperatorLandPacked,
                        220: _WriteFFOperatorSeaPacked,
                        122: _WriteFFOperatorCray32LandPacked,
                        222: _WriteFFOperatorCray32SeaPacked,                        
                        }
