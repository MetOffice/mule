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
This module provides a series of classes to allow interaction with various
file formats from the UM system

"""
from __future__ import (absolute_import, division, print_function)

import os
import tempfile
import numpy as np
from contextlib import contextmanager

# UM fixed length header names and positions
_UM_FIXED_LENGTH_HEADER = [
    ('data_set_format_version',          1   ),
    ('sub_model',                        2   ),
    ('vert_coord_type',                  3   ),
    ('horiz_grid_type',                  4   ),
    ('dataset_type',                     5   ),
    ('run_identifier',                   6   ),
    ('experiment_number',                7   ),
    ('calendar',                         8   ),
    ('grid_staggering',                  9   ),
    ('time_type',                        10  ),
    ('projection_number',                11  ),
    ('model_version',                    12  ),
    ('obs_file_type',                    14  ),
    ('last_fieldop_type',                15  ),
    ('integer_constants_start',          100 ),    
    ('integer_constants_length',         101 ),
    ('real_constants_start',             105 ),    
    ('real_constants_length',            106 ),
    ('level_dependent_constants_start',  110 ),
    ('level_dependent_constants_dim1',   111 ),
    ('level_dependent_constants_dim2',   112 ),
    ('row_dependent_constants_start',    115 ),
    ('row_dependent_constants_dim1',     116 ),
    ('row_dependent_constants_dim2',     117 ),
    ('column_dependent_constants_start', 120 ),
    ('column_dependent_constants_dim1',  121 ),
    ('column_dependent_constants_dim2',  122 ),    
    ('fields_of_constants_start',        125 ),
    ('fields_of_constants_dim1',         126 ),
    ('fields_of_constants_dim2',         127 ),    
    ('extra_constants_start',            130 ),
    ('extra_constants_length',           131 ),    
    ('temp_historyfile_start',           135 ),
    ('temp_historyfile_length',          136 ),    
    ('compressed_field_index1_start',    140 ),
    ('compressed_field_index1_length',   141 ),    
    ('compressed_field_index2_start',    142 ),
    ('compressed_field_index2_length',   143 ),    
    ('compressed_field_index3_start',    144 ),
    ('compressed_field_index3_length',   145 ),    
    ('lookup_start',                     150 ),
    ('lookup_dim1',                      151 ),
    ('lookup_dim2',                      152 ),    
    ('total_prognostic_fields',          153 ),
    ('data_start',                       160 ),
    ('data_dim1',                        161 ), 
    ('data_dim2',                        162 ),
    ]
    

# UM FieldsFile/PP LOOKUP header names and positions for header release vn.2
_LOOKUP_HEADER_2 = [
        ('lbyr',    1  ),
        ('lbmon',   2  ),
        ('lbdat',   3  ),
        ('lbhr',    4  ),
        ('lbmin',   5  ),
        ('lbday',   6  ),
        ('lbyrd',   7  ),
        ('lbmond',  8  ),
        ('lbdatd',  9  ),
        ('lbhrd',   10 ),
        ('lbmind',  11 ),
        ('lbdayd',  12 ),
        ('lbtim',   13 ),
        ('lbft',    14 ),
        ('lblrec',  15 ),
        ('lbcode',  16 ),
        ('lbhem',   17 ),
        ('lbrow',   18 ),
        ('lbnpt',   19 ),
        ('lbext',   20 ),
        ('lbpack',  21 ),
        ('lbrel',   22 ),
        ('lbfc',    23 ),
        ('lbcfc',   24 ),
        ('lbproc',  25 ),
        ('lbvc',    26 ),
        ('lbrvc',   27 ),
        ('lbexp',   28 ),
        ('lbegin',  29 ),
        ('lbnrec',  30 ),
        ('lbproj',  31 ),
        ('lbtyp',   32 ),
        ('lblev',   33 ),
        ('lbrsvd1', 34 ),
        ('lbrsvd2', 35 ),
        ('lbrsvd3', 36 ),
        ('lbrsvd4', 37 ),        
        ('lbsrce',  38 ),
        ('lbuser1', 39 ),
        ('lbuser2', 40 ),
        ('lbuser3', 41 ),
        ('lbuser4', 42 ),
        ('lbuser5', 43 ),
        ('lbuser6', 44 ),
        ('lbuser7', 45 ),                
        ('brsvd1',  46 ),
        ('brsvd2',  47 ),
        ('brsvd3',  48 ),
        ('brsvd4',  49 ),        
        ('bdatum',  50 ),
        ('bacc',    51 ),
        ('blev',    52 ),
        ('brlev',   53 ),
        ('bhlev',   54 ),
        ('bhrlev',  55 ),
        ('bplat',   56 ),
        ('bplon',   57 ),
        ('bgor',    58 ),
        ('bzy',     59 ),
        ('bdy',     60 ),
        ('bzx',     61 ),
        ('bdx',     62 ),
        ('bmdi',    63 ),
        ('bmks',    64 ),
    ]

# UM FieldsFile/PP LOOKUP header names and positions for header release vn.3
# These are identical to header release vn.2 above apart from the 6th and 12th
# elements, which had their meanings changed from "day of year" to "second"
_LOOKUP_HEADER_3 = [(name, position) for name, position in _LOOKUP_HEADER_2]
_LOOKUP_HEADER_3[5] = ('lbsec', 6 )
_LOOKUP_HEADER_3[11] = ('lbsecd', 12 )

# A mapping from header-release-number to header definition
_LOOKUP_HEADERS = {2: _LOOKUP_HEADER_2, 3: _LOOKUP_HEADER_3}

# Global default word (record) size (in bytes)
DEFAULT_WORD_SIZE = 8

# Metaclass for header objects
class _HeaderMetaclass(type):
    """
    This metaclass is used in the construction of several header-like classes
    in this module; note that it is applied on *defining* the classes (i.e.
    when this module is imported), *not* later when a specific instance of the
    classes is initialised.

    The purpose of this class is to attach a set of named attributes to the
    header object and associate these with specific indices of the underlying
    array of header values.  The target class defines this "mapping" itself,
    allowing this metaclass to be used for multiple header-like objects.
    
    """
    def __new__(metacls, classname, bases, class_dict):
        """
        Called upon definition of the target class to add the named attributes.
        The target class should define a HEADER_MAPPING attribute to specify
        the mapping to be used for the attributes.
        
        """
        # This method will return a new "getter"; which retrieves a set of
        # indices from the named attribute containing the actual value array
        # inside the target class
        def make_getter(array_attribute, indices):
            def getter(self):
                return getattr(self, array_attribute)[indices]
            return getter

        # ... and this one does the same thing but returns a "setter" to allow
        # assignment of values to the array inside the target class
        def make_setter(array_attribute, indices):
            def setter(self, values):
                getattr(self, array_attribute)[indices] = values
            return setter
        
        # Retrieve the desired mapping defined by the target class
        mapping = class_dict.get("HEADER_MAPPING")
        if mapping is not None:
            for name, indices in mapping:
                # Add a new named attribute to the class under the name given
                # in the mapping, and use the two functions above to provide
                # the methods to get + set the attribute appropriately
                class_dict[name] = property(make_getter("_values", indices),
                                            make_setter("_values", indices))

        # Finish construction of the class
        return super(_HeaderMetaclass, metacls).__new__(metacls, classname,
                                                        bases, class_dict)

class FixedLengthHeader(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass

    HEADER_MAPPING = _UM_FIXED_LENGTH_HEADER
    NUM_WORDS = 256
    MDI = -32768

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators
    @classmethod
    def empty(cls, word_size=DEFAULT_WORD_SIZE):
        integers = np.empty(cls.NUM_WORDS, dtype='>i{0}'.format(word_size))
        integers[:] = cls.MDI
        return cls(integers, word_size)

    # The from_file classmethod operates on a file to extract the header;
    # unlike the other header components this is the only one which assumes
    # the given size for the header
    @classmethod
    def from_file(cls, source, word_size=DEFAULT_WORD_SIZE):
        source.seek(0)
        integers = np.fromfile(source, dtype='>i{0}'.format(word_size),
                               count=cls.NUM_WORDS)
        return cls(integers, word_size)

    # In either case the init method will be called - it takes the raw array
    # of integers and casts them into an object array; so that the zero-th
    # element can appear as "None" - this makes it behave a little more like
    # a Fortran array in terms of the header mappings and when the user is
    # accessing it via the "raw" property
    def __init__(self, integers, word_size=DEFAULT_WORD_SIZE):

        # An extra check here, since it is paramount that fixed length headers
        # have the exact expected number of words (the other header elements
        # are slightly less strict)
        if len(integers) != self.NUM_WORDS:
            _msg = ('Incorrect number of words for {0} - given {1} but '
                    'should be {2}.'.format(type(self).__name__,
                                            len(integers), self.NUM_WORDS))
            raise ValueError(_msg)
        self._values = np.empty(self.NUM_WORDS + 1, dtype=object)
        self._values[1:] = np.asarray(integers,
                                      dtype=">i{0}".format(word_size))

    # If called - writes the the array to the given output file
    def to_file(self, fieldsfile, output_file, word_size=DEFAULT_WORD_SIZE):
        output_file.write(self._values[1:].astype('>i{0}'.format(word_size)))

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    def copy(self):
        new = type(self).empty()
        new._values = self._values.copy()
        return new

    def __eq__(self, other):
        try:
            eq = np.all(self._values == other._values)
        except AttributeError:
            eq = NotImplemented
        return eq

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result


class IntegerConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = FixedLengthHeader.MDI

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_words=0, word_size=DEFAULT_WORD_SIZE):
        return cls([cls.MDI]*num_words, word_size)

    # The from_file classmethod operates on an existing fieldsfile object
    # to extract the header
    @classmethod
    def from_file(cls, fieldsfile, word_size=DEFAULT_WORD_SIZE):
        source = fieldsfile._source
        flh = fieldsfile.fixed_length_header

        # The start position and shape of the integer constants comes from
        # the fixed length header
        start = flh.integer_constants_start
        shape = flh.integer_constants_length
        if start > 0:
            source.seek((start - 1) * word_size)
            integers = np.fromfile(source, dtype='>i{0}'.format(word_size),
                                   count=shape)
            return cls(integers, word_size)
        else:
            return None

    # If called, the init method takes the raw array of integers and casts
    # them into an object array; so that the zero-th element can appear as
    # "None" - this makes it behave a little more like a Fortran array in
    # terms of the header mappings and when the user is accessing it via
    # the "raw" property
    def __init__(self, integers, word_size=DEFAULT_WORD_SIZE):
        self._values = np.empty(len(integers) + 1, dtype=object)
        self._values[1:] = np.asarray(integers,
                                      dtype=">i{0}".format(word_size))

    # If called - writes the the array to the given output file
    def to_file(self, fieldsfile, output_file, word_size=DEFAULT_WORD_SIZE):
        flh = fieldsfile.fixed_length_header
        flh.integer_constants_start = int(output_file.tell() / word_size + 1)
        flh.integer_constants_length = self.size            
        output_file.write(self._values[1:].astype('>i{0}'.format(word_size)))

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()        

    @property
    def size(self):
        return self._values.size - 1

    def copy(self):
        new = type(self).empty()
        new._values = self._values.copy()
        return new

class RealConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = -1073741824.0

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_words=0, word_size=DEFAULT_WORD_SIZE):
        return cls([cls.MDI]*num_words, word_size)

    # The from_file classmethod operates on an existing fieldsfile object
    # to extract the header
    @classmethod
    def from_file(cls, fieldsfile, word_size=DEFAULT_WORD_SIZE):
        source = fieldsfile._source
        flh = fieldsfile.fixed_length_header

        # The start position and shape of the integer constants comes from
        # the fixed length header; start by reading in however many values
        # the file claims it contains
        start = flh.real_constants_start
        shape = flh.real_constants_length
        if start > 0:
            source.seek((start - 1) * word_size)
            reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                                count=shape)
            return cls(reals, word_size)
        else:
            return None

    # If called, the init method takes the raw array of integers and casts
    # them into an object array; so that the zero-th element can appear as
    # "None" - this makes it behave a little more like a Fortran array in
    # terms of the header mappings and when the user is accessing it via
    # the "raw" property
    def __init__(self, reals, word_size=DEFAULT_WORD_SIZE):
        self._values = np.empty(len(reals) + 1, dtype=object)
        self._values[1:] = np.asarray(reals,
                                      dtype=">f{0}".format(word_size))

    # If called - writes the the array to the given output file
    def to_file(self, fieldsfile, output_file, word_size=DEFAULT_WORD_SIZE):
        flh = fieldsfile.fixed_length_header
        flh.real_constants_start = int(output_file.tell() / word_size + 1)
        flh.real_constants_length = self.size            
        output_file.write(self._values[1:].astype('>f{0}'.format(word_size)))
        
    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()
    
    @property
    def size(self):
        return self._values.size - 1
    
    def copy(self):
        new = type(self).empty()
        new._values = self._values.copy()
        return new


class LevelDependentConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = RealConstants.MDI

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_levels=0, num_cols=0, word_size=DEFAULT_WORD_SIZE):
        reals = np.empty((num_levels, num_cols),
                         dtype='>f{0}'.format(word_size))
        reals[:,:] = cls.MDI
        return cls(reals, word_size)

    # The from_file classmethod operates on an existing fieldsfile object
    # to extract the header
    @classmethod
    def from_file(cls, fieldsfile, word_size=DEFAULT_WORD_SIZE):
        source = fieldsfile._source
        flh = fieldsfile.fixed_length_header

        # The start position and shape of the integer constants comes from
        # the fixed length header; start by reading in however many values
        # the file claims it contains
        start = flh.level_dependent_constants_start
        n_levels = flh.level_dependent_constants_dim1
        n_cols = flh.level_dependent_constants_dim2
        
        if start > 0:
            source.seek((start - 1) * word_size)
            reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                                count=np.product((n_levels, n_cols)))
            reals = reals.reshape((n_levels, n_cols), order="F")
            return cls(reals, word_size)
        else:
            return None

    # If called, the init method takes the raw array of integers and casts
    # them into an object array; so that the zero-th element can appear as
    # "None" - this makes it behave a little more like a Fortran array in
    # terms of the header mappings and when the user is accessing it via
    # the "raw" property
    def __init__(self, reals, word_size=DEFAULT_WORD_SIZE):
        self._values = np.empty((reals.shape[0], reals.shape[1] + 1),
                                 dtype=object)
        self._values[:,1:] = reals

    # If called - writes the the array to the given output file
    def to_file(self, fieldsfile, output_file, word_size=DEFAULT_WORD_SIZE):
        flh = fieldsfile.fixed_length_header
        flh.level_dependent_constants_start = int(output_file.tell() / word_size + 1)
        flh.level_dependent_constants_dim1 = self._values.shape[0]
        flh.level_dependent_constants_dim2 = self._values.shape[1] - 1        
        output_file.write(np.ravel(
            self._values[:,1:].astype('>f{0}'.format(word_size)), order="F"))

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    @property
    def size(self):
        return self._values.size - self._values.shape[0]

    def copy(self):
        new = type(self).empty(self._values.shape[0])
        new._values = self._values.copy()
        return new


class RowDependentConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = RealConstants.MDI

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_rows=0, num_grids=0, word_size=DEFAULT_WORD_SIZE):
        reals = np.empty((num_rows, num_grids), dtype='>f{0}'.format(word_size))
        reals[:,:] = cls.MDI
        return cls(reals, word_size)

    # The from_file classmethod operates on an existing fieldsfile object
    # to extract the header
    @classmethod
    def from_file(cls, fieldsfile, word_size=DEFAULT_WORD_SIZE):
        source = fieldsfile._source
        flh = fieldsfile.fixed_length_header

        # The start position and shape of the integer constants comes from
        # the fixed length header; start by reading in however many values
        # the file claims it contains
        start = flh.row_dependent_constants_start
        n_rows = flh.row_dependent_constants_dim1
        n_grids = flh.row_dependent_constants_dim2

        if start > 0:
            source.seek((start - 1) * word_size)
            reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                                count=np.product((n_grids, n_rows)))
            reals = reals.reshape((n_rows, n_grids), order="F")
            return cls(reals, word_size)
        else:
            return None

    # If called, the init method takes the raw array of integers and casts
    # them into an object array; so that the zero-th element can appear as
    # "None" - this makes it behave a little more like a Fortran array in
    # terms of the header mappings and when the user is accessing it via
    # the "raw" property
    def __init__(self, reals, word_size=DEFAULT_WORD_SIZE):
        self._values = np.empty((reals.shape[0], reals.shape[1]+1),
                                 dtype=object)
        self._values[:,1:] = reals

    # If called - writes the the array to the given output file
    def to_file(self, fieldsfile, output_file, word_size=DEFAULT_WORD_SIZE):
        flh = fieldsfile.fixed_length_header
        flh.row_dependent_constants_start = int(output_file.tell() / word_size + 1)
        flh.row_dependent_constants_dim1 = self._values.shape[0]
        flh.row_dependent_constants_dim2 = self._values.shape[1] - 1        
        output_file.write(np.ravel(
            self._values[:,1:].astype('>f{0}'.format(word_size)), order="F"))
        
    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    @property
    def size(self):
        return self._values.size - self._values.shape[0]

    def copy(self):
        new = type(self).empty(self._values.shape[0])
        new._values = self._values.copy()
        return new

class ColumnDependentConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = RealConstants.MDI

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_cols=0, num_grids=0, word_size=DEFAULT_WORD_SIZE):
        reals = np.empty((num_cols, num_grids), dtype='>f{0}'.format(word_size))
        reals[:,:] = cls.MDI
        return cls(reals, word_size)

    # The from_file classmethod operates on an existing fieldsfile object
    # to extract the header
    @classmethod
    def from_file(cls, fieldsfile, word_size=DEFAULT_WORD_SIZE):
        source = fieldsfile._source
        flh = fieldsfile.fixed_length_header

        # The start position and shape of the integer constants comes from
        # the fixed length header; start by reading in however many values
        # the file claims it contains
        start = flh.column_dependent_constants_start
        n_cols = flh.column_dependent_constants_dim1
        n_grids = flh.column_dependent_constants_dim2
        
        if start > 0:
            source.seek((start - 1) * word_size)
            reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                                count=np.product((n_grids, n_cols)))
            reals = reals.reshape((n_cols, n_grids), order="F")
            return cls(reals, word_size)
        else:
            return None

    # If called, the init method takes the raw array of integers and casts
    # them into an object array; so that the zero-th element can appear as
    # "None" - this makes it behave a little more like a Fortran array in
    # terms of the header mappings and when the user is accessing it via
    # the "raw" property
    def __init__(self, reals, word_size=DEFAULT_WORD_SIZE):
        self._values = np.empty((reals.shape[0], reals.shape[1] + 1),
                                 dtype=object)
        self._values[:,1:] = reals

    # If called - writes the the array to the given output file
    def to_file(self, fieldsfile, output_file, word_size=DEFAULT_WORD_SIZE):
        flh = fieldsfile.fixed_length_header
        flh.column_dependent_constants_start = int(output_file.tell() / word_size + 1)
        flh.column_dependent_constants_dim1 = self._values.shape[0]
        flh.column_dependent_constants_dim2 = self._values.shape[1] - 1
        output_file.write(np.ravel(
            self._values[:,1:].astype('>f{0}'.format(word_size)), order="F"))

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    @property
    def size(self):
        return self._values.size - self._values.shape[0]
    
    def copy(self):
        new = type(self).empty(self._values.shape[0])
        new._values = self._values.copy()
        return new


class Field(object):
    """
    Represents a single entry in the LOOKUP component and its
    corresponding section of the DATA component.
    
    """
    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass

    # The number of lookup entries which are integers and reals
    NUM_LOOKUP_INTS = 45
    NUM_LOOKUP_REALS = 19

    # Zero-based index for lblrec.
    LBLREC_OFFSET = 14
    # Zero-based index for lbrel.
    LBREL_OFFSET = 21
    # Zero-based index for lbegin.
    LBEGIN_OFFSET = 28
    # Zero-based index for lbnrec.
    LBNREC_OFFSET = 29

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, word_size=DEFAULT_WORD_SIZE):
        integers = np.empty(cls.NUM_LOOKUP_INTS,
                            dtype='>i{0}'.format(word_size))
        integers[:] = -99
        reals = np.empty(cls.NUM_LOOKUP_REALS,
                         dtype='>f{0}'.format(word_size))
        reals[:] = 0.0
        
        return cls(integers, reals, None)

    def __init__(self, int_headers, real_headers, data_provider):
        """
        Create a Field from the integer headers, the floating-point
        headers, and an object which provides access to the
        corresponding data.

        Args:

        * int_headers:
            A sequence of integer header values.
        * real_headers:
            A sequence of floating-point header values.
        * data_provider:
            A subclass of _DataProvider which returns the data
            referred to by this field object

        """
        # Create a numpy object array to hold the entire lookup, leaving a
        # space for the zeroth index so that it behaves like the 1-based
        # indexing referred to in UMDP F03
        self._values = np.ndarray( len(int_headers) + len(real_headers) + 1,
                                  dtype=object)
        # Populate the first half with the integers
        self._values[1:len(int_headers)+1] = (
            np.asarray(int_headers, dtype=">i{0}".format(DEFAULT_WORD_SIZE)))
        # And the rest with the real values
        self._values[len(int_headers)+1:] = (
            np.asarray(real_headers, dtype=">f{0}".format(DEFAULT_WORD_SIZE)))

        # Create views onto the above array to retrieve the integer/real
        # parts of the lookup header separately (for writing out)
        self._lookup_ints = self._values[1:len(int_headers)+1]
        self._lookup_reals = self._values[len(int_headers)+1:]

        # Save the reference to the given _DataProvider
        self.data_provider = data_provider

    def to_file(self, fieldsfile, output_file, word_size=DEFAULT_WORD_SIZE):
        output_file.write(self._values[1:self.NUM_LOOKUP_INTS+1]
                          .astype(">i{0}".format(word_size)))
        output_file.write(self._values[self.NUM_LOOKUP_INTS+1:]
                          .astype(">f{0}".format(word_size)))

    def __eq__(self, other):
        try:
            is_eq = (np.all(self._values == other._values) and
                     np.all(self.get_data() == other.get_data()))
        except AttributeError:
            is_eq = NotImplemented
        return is_eq

    def __ne__(self, other):
        result = self.__eq__(other)
        if result is not NotImplemented:
            result = not result
        return result

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    def copy(self):
        """
        Create a Field which copies its header information from this one.
        
        """
        new_field = type(self) (self._lookup_ints.copy(),
                                self._lookup_reals.copy(),
                                self.data_provider)
        return new_field

    def num_values(self):
        """
        Return the number of values defined by this header.
        
        """
        return len(self._values) - 1

    def get_data(self):
        """
        Return a NumPy array containing the data for this field.

        The field's data_provider is a flexible object which a user
        may extend and override to perform various manipulations and
        transformations of the data using a DataOperator subclass.
        
        """
        data = None
        if self.data_provider is not None:
            data = self.data_provider.data
        return data

    def _get_raw_payload_bytes(self):
        """
        Return a buffer containing the raw bytes of the data payload.

        The field data must be unmodified and using the same packing
        code as the original data (this can be tested by calling
        _can_copy_deferred_data).
        
        """
        if issubclass(type(self.data_provider), _RawReadProvider):
            return self.data_provider._read_bytes()
        else:
            return None

    def _can_copy_deferred_data(self, required_lbpack, required_bacc):
        """
        Return whether or not it is possible to simply re-use the bytes
        making up the field; for this to be possible the data must be
        unmodified, and the requested output packing must be the same
        as the input packing.
        
        """
        # Whether or not this is possible depends on if the Fields
        # data provider has been wrapped in any operations
        compatible = issubclass(type(self.data_provider), _RawReadProvider)
        if compatible:
            src_lbpack = self.data_provider.source.lbpack
            src_bacc = self.data_provider.source.bacc
            # The packing words are compatible if nothing else is different.
            compatible = (required_lbpack == src_lbpack and
                          required_bacc == src_bacc)

        return compatible


class Field2(Field):
    """
    Represents an entry from the LOOKUP component with a header release
    number of 2.

    """
    HEADER_MAPPING = _LOOKUP_HEADERS[2]


class Field3(Field):
    """
    Represents an entry from the LOOKUP component with a header release
    number of 3.

    """
    HEADER_MAPPING = _LOOKUP_HEADERS[3]


class _DataProvider(object):
    """
    This class provides the means to wrap a Field object's existing data
    provider with a new one; consisting of the product of the field and
    a data operator capable of returning the data array.
    
    """
    def __init__(self, operator, source):
        """
        Initialise the wrapper, saving a reference to the data operator
        and the field/s it will be applied to.
        
        """
        self.operator = operator
        self.source = source
    @property
    def data(self):
        """
        Return the data using the provided operator.
        
        """
        return self.operator.transform(self.source)

    
class DataOperator(object):
    """
    Base class which should be sub-classed to perform manipulations on the
    data of a field.  The Field classes never store any data directly in
    memory; only the means to retrieve it from disk and perform any required
    operations (which will only be executed when explicitly requested - this
    would normally be at the point the file is being written/closed).

    The user must override the following methods to produce a functional
    operator:

      * __init__(self, *args, **kwargs)
        This method should accept any user arguments to be "baked" into the
        operator or to otherwise initialise it as-per the user's requirements;
        for example an operator which scales the values in fields by a
        constant amount might want to accept an argument giving that amount.

      * __call__(self, source, *args, **kwargs)
        This method needs to return a Field instance corresponding to the new
        field object resulting from the operator.  Normally the first argument
        will be one or more existing Field objects; note that these should not
        be modified by the operator (take a copy if needed).  In order to apply
        the operator to the source Field/s the bind_operator method must be
        called as part of this method.  If the operator is desigend to update
        any of the Field's lookup headers this is where it should do so.

      * transform(self, field)
        This method represents the work carried out by the operator on the
        source Field/s to produce and return a new data array.  It should
        return a numpy array containing the (modified) field data.
        
    """
    def bind_operator(self, new_field, source):
        """
        Use the _DataProvider class to bind the action of this operator to
        the field's data_provider.
        
        """
        new_field.data_provider = _DataProvider(self, source)

        
class _RawReadProvider(_DataProvider):
    """
    A special _DataProvider subclass, which deals with the most basic/common
    data-provision operation of reading in Field data from a file.  This class
    should not be used directly - since it does not define a "data" property
    and so cannot return any data.  A series of subclasses of this class are
    provided which define the property for the different packing types found
    in FieldsFileVariants
        
    """
    def __init__(self, source, sourcefile, offset, word_size):
        """
        Initialise the _RawReadOperator.

        Args:

        * source:
            Initial field object reference (populated with the lookup values
            from the file specified in sourcefile.

        * sourcefile:
            Filename associated with source FieldsFileVariant.

        * offset:
            Starting position of Field data in sourcefile (in bytes).

        * word_size:
            Word size of Field data (in bytes).
        
        """
        self.source = source
        self.sourcefile = sourcefile
        self.offset = offset
        self.word_size = word_size

    @contextmanager
    def _with_source(self):
        # Context manager to temporarily reopen the sourcefile if the original
        # provided at create time has been closed.
        reopen_required = self.sourcefile.closed
        close_required = False
        try:
            if reopen_required:
                self.sourcefile = open(self.sourcefile.name)
                close_required = True
            yield self.sourcefile
        finally:
            if close_required:
                self.sourcefile.close()

    def _read_bytes(self):
        # Return the raw data payload, as an array of bytes.
        # This is independent of the content type.
        field = self.source
        with self._with_source():
            self.sourcefile.seek(self.offset)
            data_size = field.lbnrec * self.word_size
            # This size calculation seems rather questionable, but derives from
            # a very long code legacy, so appeal to a "sleeping dogs" policy.
            data_bytes = self.sourcefile.read(data_size)
        return data_bytes

class _NullReadProvider(_RawReadProvider):
    """
    A _DataProvider to use when a packing code is unrecognised - to allow
    the headers to still be associated
    """
    @property
    def data(self):
        lbpack = self.source.raw[21]
        raise NotImplementedError("Packing code {0} unsupported".format(lbpack))


class UMFile(object):
    """
    Represents a single UM file with a structure similar to what is described
    In UMDP F03

    """
    # The dataset types for any UM File variant
    _DATASET_TYPES = []

    # The components found in the file header (after the initial fixed-length
    # header), and their types
    _COMPONENTS = (('integer_constants', IntegerConstants),
                   ('real_constants', RealConstants),
                   ('level_dependent_constants', LevelDependentConstants),
                   ('row_dependent_constants', RowDependentConstants),
                   ('column_dependent_constants', ColumnDependentConstants))  

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _DataProvider to use for the reading, for FieldsFiles
    _READ_PROVIDERS = {}

    # Mappings from the leading 3-digits of the lbpack LOOKUP header to the
    # equivalent _WriteFFOperator to use for writing, for FieldsFiles
    _WRITE_OPERATORS = {}
        
    # Maps lbrel to a Field class.
    # Maps lbrel to a Field class.
    _FIELD_CLASSES = {2: Field2, 3: Field3, -99: Field}
    _FIELD = _FIELD_CLASSES[-99]

    # Data alignment values (to match with UM definitions)
    _WORDS_PER_SECTOR = 512        # Padding for each field (in words)
    _DATA_START_ALIGNMENT = 524288 # Padding to start of data (in bytes)

    class _Mode(object):
        def __init__(self, name):
            self.name = name

        def __repr__(self):
            return self.name

    #: The file will be opened for read-only access.
    READ_MODE = _Mode('READ_MODE')
    #: The file will be opened for update.
    UPDATE_MODE = _Mode('UPDATE_MODE')
    #: The file will be created, overwriting the file if it already
    #: exists.
    CREATE_MODE = _Mode('CREATE_MODE')

    _MODE_MAPPING = {READ_MODE: 'rb', UPDATE_MODE: 'r+b', CREATE_MODE: 'wb'}

    @classmethod
    def from_existing(cls, existing_ffv, filename):
        """
        Create a new FieldsFile object from an existing one; this will
        copy all headers from the provided existing object, but none of the
        field objects (the "fields" attribute will be an empty list).

        Args:

        * existing_ffv:
            The existing FieldsFile object to copy from.

        * filename:
            A new FieldsFile must be associated with a filename; this
            file will be created immediately and written when the "close"
            method is called.
        
        """
        if type(existing_ffv) is not cls:
            _msg = ("Cannot copy from {0}, expecting {1}"
                    .format(type(existing_ffv), cls))
            raise ValueError(_msg)

        # Create a new object, with the same word size
        new_ffv = cls(filename, mode=cls.CREATE_MODE,
                      word_size=existing_ffv._word_size)

        # Copy the fixed length header from the source FieldsFile
        new_ffv.fixed_length_header = existing_ffv.fixed_length_header.copy()

        # Copy each other header component from the source FieldsFile
        for name, _ in existing_ffv._COMPONENTS:
            component = getattr(existing_ffv, name)
            if component is not None:
                setattr(new_ffv, name, component.copy())
            else:
                setattr(new_ffv, name, component)

        return new_ffv

    def __init__(self, filename, mode=READ_MODE, word_size=DEFAULT_WORD_SIZE):
        """
        Opens the given filename as a UM FieldsFile.

        Args:

        * filename:
            The name of the file containing the UM FieldsFile.

        Kwargs:

        * mode:
            The file access mode: `READ_MODE` for read-only;
            `UPDATE_MODE` for amending; `CREATE_MODE` for creating a new
            file.

        * word_size:
            The number of byte in each word.

        """
        if mode not in self._MODE_MAPPING:
            _msg = 'Invalid access mode: {0}'.format(mode)
            raise ValueError(_msg)

        self._filename = filename
        self._mode = mode
        self._word_size = word_size

        source_mode = self._MODE_MAPPING[mode]
        self._source = source = open(filename, source_mode)
        
        if mode is self.CREATE_MODE:
            header = FixedLengthHeader.empty(word_size)
        else:
            header = FixedLengthHeader.from_file(source, word_size)
            # Check to see if the dataset type matches what is expected by
            # this class/subclass
            if (len(self._DATASET_TYPES) > 0
                and header.dataset_type not in self._DATASET_TYPES):
                _msg = ("Trying to read in file with dataset_type {0}; "
                        "allowed types for {1} are {2}".format(
                         header.dataset_type, type(self).__name__,
                         str(self._DATASET_TYPES)))
                raise ValueError(_msg)
            
        self.fixed_length_header = header

        # Apply the appropriate headerclass from each component
        for name, headerclass in self._COMPONENTS:
            if mode is self.CREATE_MODE:
                setattr(self, name, None)
            else:
                setattr(self, name, headerclass.from_file(self, word_size))
        
        int_dtype = '>i{0}'.format(word_size)
        real_dtype = '>f{0}'.format(word_size)

        lookup_start = self.fixed_length_header.lookup_start
        if lookup_start > 0:
            source.seek((lookup_start - 1)*word_size)

            shape = (self.fixed_length_header.lookup_dim1,
                     self.fixed_length_header.lookup_dim2)
        
            lookup = np.fromfile(source, dtype=int_dtype, count=np.product(shape))
            lookup = lookup.reshape(shape, order = "F")
        else:
            lookup = None

        fields = []
        if lookup is not None:
            is_model_dump = lookup[self._FIELD.LBNREC_OFFSET, 0] == 0
            if is_model_dump:
                # A model dump has no direct addressing - only relative,
                # so we need to update the offset as we create each
                # Field.
                running_offset = ((self.fixed_length_header.data_start - 1) *
                                  word_size)

            # A list to store references to land packed fields, and a dummy
            # variable to hold the reference to the land-sea mask (if found)
            land_packed_fields = []
            land_sea_mask = None

            for raw_headers in lookup.T:
                ints = raw_headers[:self._FIELD.NUM_LOOKUP_INTS]
                reals = raw_headers[self._FIELD.NUM_LOOKUP_INTS:].view(real_dtype)
                field_class = self._FIELD_CLASSES.get(
                    ints[self._FIELD.LBREL_OFFSET], self._FIELD)
                if raw_headers[0] == -99:
                    provider = None
                else:
                    if is_model_dump:
                        offset = running_offset
                    else:
                        offset = raw_headers[self._FIELD.LBEGIN_OFFSET] * word_size
                    # Make a *copy* of field lookup data, as it was in the
                    # untouched original file, as a context for data loading.
                    lookup_reference = field_class(ints.copy(), reals.copy(),
                                                   None)

                    # Now select which type of basic reading and unpacking
                    # provider is suitable for the type of file and data,
                    # starting by checking the number format (N4 position)
                    lbpack = ints[20]
                    num_format = (lbpack//1000) % 10
                    # Check number format is valid
                    if  num_format not in (0, 2, 3):
                        msg = 'Unsupported number format (lbpack N4): {0}'
                        raise ValueError(msg.format(format))

                    # With that check out of the way remove the N4 digit and
                    # proceed with the N1 - N3 digits
                    lbpack321 = lbpack - num_format*1000

                    # These will be the basic arguments to any of the providers
                    # selected below, since they all inherit from the same
                    # _RawReadProvider class
                    args = (lookup_reference, source, offset, word_size)

                    if self._READ_PROVIDERS.has_key(lbpack321):
                        provider = (
                            self._READ_PROVIDERS[lbpack321](*args))
                    else:
                        provider = _NullReadProvider(*args)

                # Create the field object, with the _RawReadOperator subclass
                # which is able to provide the data from the file
                field = field_class(ints, reals, provider)
                fields.append(field)

                # If this object was the Land-Sea mask, save a reference to it
                if hasattr(field, "lbuser4"):
                    if field.lbuser4 == 30:
                        land_sea_mask = field

                # If this object is using a form of Land/Sea packing, update
                # its reference to the land_sea_mask (if available), otherwise
                # save a reference to it for checking later
                if hasattr(field.data_provider, "LAND"):
                    if land_sea_mask is not None:
                        field.data_provider.lsm_source = land_sea_mask
                    else:
                        land_packed_fields.append(field)

                # Update the running offset if required
                if is_model_dump:
                    running_offset += (raw_headers[self._FIELD.LBLREC_OFFSET] *
                                       word_size)

            # If any fields were land-packed but encountered before the Land/Sea
            # mask, update their references to it here
            for field in land_packed_fields:
                if land_sea_mask is not None:
                    field.data_provider.lsm_source = land_sea_mask

        self.fields = fields

    def __del__(self):
        if hasattr(self, '_source'):
            self.close()

    def __str__(self):
        items = []
        for name, kind in self._COMPONENTS:
            value = getattr(self, name)
            if value is not None:
                items.append('{0}={1}'.format(name, value.shape))
        if self.fields:
            items.append('fields={0}'.format(len(self.fields)))
        return '<{0}: {1}>'.format(type(self).__name__,', '.join(items))

    def __repr__(self):
        fmt = '<{0}: fields={1}>'
        return fmt.format(type(self).__name__, len(self.fields))

    @property
    def filename(self):
        return self._filename

    @property
    def mode(self):
        return self._mode

    def purge_empty_lookups(self):
        """
        Calling this method will delete any fields from the field list
        which are empty.
        
        """
        self.fields = [field for field in self.fields
                       if field.raw[1] != -99]

    def _calc_lookup_and_data_positions(self, lookup_start):
        # Calculate the positional data for the lookup and data parts of the
        header = self.fixed_length_header
        if self.fields:
            header.lookup_start = lookup_start
            lookup_lengths = set([field.num_values() for field in self.fields])
            if len(lookup_lengths) != 1:
                msg = 'Inconsistent lookup header lengths - {0}'
                raise ValueError(msg.format(lookup_lengths))
            lookup_length = lookup_lengths.pop()
            n_fields = len(self.fields)
            header.lookup_dim1 = lookup_length
            header.lookup_dim2 = n_fields

            # make space for the lookup
            word_number = lookup_start + lookup_length * n_fields
            # Round up to the nearest whole number of "sectors".
            offset = word_number - 1
            offset -= offset % -self._DATA_START_ALIGNMENT
            header.data_start = offset + 1

    def _write_singular_headers(self, output_file):
        # Skip past the fixed length header for now
        output_file.seek(self.fixed_length_header.NUM_WORDS * self._word_size)

        # Go through each component defined for this file type
        for name, _ in self._COMPONENTS:
            component = getattr(self, name)
            if component is not None:
                # Write it out to the file; note a reference to this file
                # object (self) is passed here, to allow the component's
                # writing routine to update/check any headers it needs to
                component.to_file(self, output_file)

    def _write_new(self, output_file):

        # Setup the output writing operators - these need to be instantiated 
        # and passed a reference to this object
        for lbpack_write in self._WRITE_OPERATORS.keys():
            self._WRITE_OPERATORS[lbpack_write] = (
                self._WRITE_OPERATORS[lbpack_write](self))

        # A reference to the header
        flh = self.fixed_length_header

        # Write the singular headers (i.e. all headers apart from the
        # lookups, which will be done below)  This will also populate most
        # of the positional values reset above
        self._write_singular_headers(output_file)

        # Update the fixed length header position entries corresponding to
        # the data and lookup
        single_headers_end =  output_file.tell() // self._word_size
        self._calc_lookup_and_data_positions(single_headers_end + 1)

        # Reset the total field count (we don't have a way of calculating
        # the correct value for it, and if we copied from an existing file
        # which did have it set it will appear incorrect now)
        flh.total_prognostic_fields = flh.MDI

        if self.fields:
            # Skip the LOOKUP component and write the DATA component.
            # We need to adjust the LOOKUP headers to match where
            # the DATA payloads end up, so to avoid repeatedly
            # seeking backwards and forwards it makes sense to wait
            # until we've adjusted them all and write them out in
            # one go.
            output_file.seek((flh.data_start - 1) * self._word_size)
            sector_size = self._WORDS_PER_SECTOR * self._word_size

            # If the land-sea mask is present, extract it here to save
            # doing so for each field that might need it (for land/sea
            # packing on output)
            for field in self.fields:
                if hasattr(field, "lbuser4"):
                    if field.lbuser4 == 30:
                        lsm = field.get_data().ravel()
                        self.land_mask = np.where(lsm == 1)[0]
                        self.sea_mask = np.where(lsm != 1)[0]
                        
            for field in self.fields:
                if hasattr(field, 'HEADER_MAPPING'):

                    # Output 'recognised' lookup types (not blank entries).
                    field.lbegin = output_file.tell() / self._word_size

                    # WGDOS packed fields can be tagged with an accuracy of
                    # -99.0; this indicates that they should not be packed,
                    # so reset the packing code here accordingly
                    if field.lbpack % 10 == 1 and int(field.bacc) == -99:
                        field.lbpack = 10*(field.lbpack//10)
                        
                    required_lbpack, required_bacc = field.lbpack, field.bacc

                    if field._can_copy_deferred_data(
                            required_lbpack, required_bacc):
                        # The original, unread file data is encoded as wanted,
                        # so extract the raw bytes and write them back out
                        # again unchanged; however first trim off any existing
                        # padding to allow the code below to re-pad the output
                        data_bytes = field._get_raw_payload_bytes()
                        data_bytes = data_bytes[:field.lblrec*self._word_size]
                        output_file.write(data_bytes)
                    else:

                        num_format = (required_lbpack//1000) % 10
                        lbpack321 = required_lbpack - num_format*1000

                        if lbpack321 not in self._WRITE_OPERATORS:
                            msg = ('Cannot save data with lbpack={0} : '
                                   'packing not supported.')
                            raise ValueError(msg.format(required_lbpack))

                        data_bytes, data_size = (
                            self._WRITE_OPERATORS[lbpack321].to_bytes(field))

                        output_file.write(data_bytes)
                        field.lblrec = data_size
                        field.lbnrec = (
                            field.lblrec - field.lblrec
                            % -self._WORDS_PER_SECTOR)

                    # Pad out the data section to a whole number of sectors.
                    overrun = output_file.tell() % sector_size
                    if overrun != 0:
                        padding = np.zeros(sector_size - overrun, 'i1')
                        output_file.write(padding)

            # Update the fixed length header to reflect the extent
            # of the DATA component.
            flh.data_dim1 = ((output_file.tell() // self._word_size)
                             - flh.data_start + 1)

            # Go back and write the LOOKUP component.
            output_file.seek((flh.lookup_start - 1) * self._word_size)
            
            for field in self.fields:
                field.to_file(self, output_file)

        # Write the fixed length header - now that we know how big
        # the DATA component was.
        output_file.seek(0)
        self.fixed_length_header.to_file(self, output_file)


    def close(self):
        """
        Write out any pending changes, and close the underlying file.

        If the file was opened for update or creation then the current
        state of the fixed length header, the constant components (e.g.
        integer_constants, level_dependent_constants), and the list of
        fields are written to the file before closing. The process of
        writing to the file also updates the values in the fixed length
        header and fields which relate to layout within the file. For
        example, `integer_constants_start` and `integer_constants_shape`
        within the fixed length header, and the `lbegin` and `lbnrec`
        elements within the fields.

        If the file was opened in read mode then no changes will be
        made.

        After calling `close()` any subsequent modifications to any of
        the attributes will have no effect on the underlying file.

        Calling `close()` more than once is allowed, but only the first
        call will have any effect.

        .. note::

            On output, each field's data is encoded according to the LBPACK
            and BACC words in the field.  However, data from the input file can
            be saved in its original packed form, as long as the data, LBPACK
            and BACC remain unchanged.

        """
        if not self._source.closed:
            try:
                if self.mode in (self.UPDATE_MODE, self.CREATE_MODE):
                    # For simplicity at this stage we always create a new
                    # file and rename it once complete.
                    # At some later stage we can optimise for in-place
                    # modifications, for example if only one of the integer
                    # constants has been modified.

                    src_dir = os.path.dirname(os.path.abspath(self.filename))
                    with tempfile.NamedTemporaryFile(dir=src_dir,
                                                     delete=False) as tmp_file:
                        self._write_new(tmp_file)
                    os.unlink(self.filename)
                    os.rename(tmp_file.name, self.filename)
                    os.chmod(self.filename, 0o644)
            finally:
                self._source.close()

# Import the derived UM File formats
from mule.ff import FieldsFile
from mule.lbc import LBCFile

# Mapping from known dataset types to the appropriate class to use
DATASET_TYPE_MAPPING = {
    1: FieldsFile,
    2: FieldsFile,
    3: FieldsFile,
    5: LBCFile,
}
    
def load_umfile(unknown_umfile):
    """
    Can be used to try and load a UM file of undetermined type, by checking
    its dataset type and trying to match it to the correct class.
    
    """
    with open(unknown_umfile, "r") as umfile:
        flh = FixedLengthHeader.from_file(umfile)
    if flh.dataset_type in DATASET_TYPE_MAPPING:
        return DATASET_TYPE_MAPPING[flh.dataset_type](unknown_umfile)
    else:
        msg = ("Unknown dataset_type {0}, supported types are {1}"
               .format(flh.dataset_type, str(DATASET_TYPE_MAPPING.keys())))
        raise ValueError(msg)

    


