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
    def __new__(cls, classname, bases, class_dict):
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
        return super(_HeaderMetaclass, cls).__new__(cls, classname,
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
    def to_file(self, output_file, word_size=DEFAULT_WORD_SIZE):
        output_file.write(self._values[1:].astype('>i{0}'.format(word_size)))

    @property
    def shape(self):
        return (self.NUM_WORDS,)

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
    CREATE_DIMS = (None,)
    # Note: subclasses can redefine this to define a default 'empty' shape.

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_words=None, word_size=DEFAULT_WORD_SIZE):
        if num_words is None:
            num_words = cls.CREATE_DIMS[0]
        if num_words is None:
            raise(ValueError('"num_words" has no valid default'))
        return cls([cls.MDI]*num_words, word_size)

    # The from_file classmethod reads the header from a file object
    @classmethod
    def from_file(cls, source, num_words, word_size=DEFAULT_WORD_SIZE):
        integers = np.fromfile(source, dtype='>i{0}'.format(word_size),
                               count=num_words)
        return cls(integers, word_size)

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
    def to_file(self, output_file, word_size=DEFAULT_WORD_SIZE):
        output_file.write(self._values[1:].astype('>i{0}'.format(word_size)))

    @property
    def shape(self):
        return self._values[1:].shape

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()        

    def copy(self):
        return type(self)(self.raw[1:])


class RealConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = -1073741824.0
    N_DIMENSIONS = 1
    CREATE_DIMS = (None,)
    # Note: subclasses can redefine this to define a default 'empty' shape.

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_words=None, word_size=DEFAULT_WORD_SIZE):
        if num_words is None:
            num_words = cls.CREATE_DIMS[0]
        if num_words is None:
            raise(ValueError('"num_words" has no valid default'))
        return cls([cls.MDI]*num_words, word_size)

    # The from_file classmethod reads the header from a file object
    @classmethod
    def from_file(cls, source, num_words, word_size=DEFAULT_WORD_SIZE):
        reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                            count=num_words)
        return cls(reals, word_size)
    
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
    def to_file(self, output_file, word_size=DEFAULT_WORD_SIZE):
        output_file.write(self._values[1:].astype('>f{0}'.format(word_size)))

    @property
    def shape(self):
        return self._values[1:].shape

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    def copy(self):
        return type(self)(self.raw[1:])


class LevelDependentConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = RealConstants.MDI
    CREATE_DIMS = (None, None)

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_levels=None, num_level_types=None, word_size=DEFAULT_WORD_SIZE):
        # NOTE: is "num_cols" the right term here ??
        if num_levels is None:
            num_levels = cls.CREATE_DIMS[0]
        if num_level_types is None:
            num_level_types = cls.CREATE_DIMS[1]
        if num_levels is None:
            raise(ValueError('"num_levels" has no valid default'))
        if num_level_types is None:
            raise(ValueError('"num_level_types" has no valid default'))
        reals = np.empty((num_levels, num_level_types),
                         dtype='>f{0}'.format(word_size))
        reals[:,:] = cls.MDI
        return cls(reals, word_size)

    # The from_file classmethod reads the header from a file object
    @classmethod
    def from_file(cls, source, num_levels, num_level_types,
                  word_size=DEFAULT_WORD_SIZE):
        reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                            count=np.product((num_levels, num_level_types)))
        reals = reals.reshape((num_levels, num_level_types), order="F")
        return cls(reals, word_size)

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
    def to_file(self, output_file, word_size=DEFAULT_WORD_SIZE):
        output_file.write(np.ravel(
            self._values[:,1:].astype('>f{0}'.format(word_size)), order="F"))

    @property
    def shape(self):
        return self._values[:, 1:].shape

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    def copy(self):
        return type(self)(self.raw[:,1:])


class RowDependentConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = RealConstants.MDI
    CREATE_DIMS = (None, None)

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_rows=0, num_grids=0, word_size=DEFAULT_WORD_SIZE):
        if num_rows is None:
            num_rows = cls.CREATE_DIMS[0]
        if num_grids is None:
            num_grids = cls.CREATE_DIMS[1]
        if num_rows is None:
            raise(ValueError('"num_rows" has no valid default'))
        if num_grids is None:
            raise(ValueError('"num_grids" has no valid default'))
        reals = np.empty((num_rows, num_grids), dtype='>f{0}'.format(word_size))
        reals[:,:] = cls.MDI
        return cls(reals, word_size)

    # The from_file classmethod reads the header from a file object
    @classmethod
    def from_file(cls, source, num_rows, num_grids,
                  word_size=DEFAULT_WORD_SIZE):
        import pdb ; pdb.set_trace()
        reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                            count=np.product((num_rows, num_grids)))
        reals = reals.reshape((num_rows, num_grids), order="F")
        return cls(reals, word_size)
    
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
    def to_file(self, output_file, word_size=DEFAULT_WORD_SIZE):
        output_file.write(np.ravel(
            self._values[:,1:].astype('>f{0}'.format(word_size)), order="F"))

    @property
    def shape(self):
        return self._values[:, 1:].shape

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    def copy(self):
        return type(self)(self.raw[:,1:])


class ColumnDependentConstants(object):

    # Preset the mappings into the array via the metaclass, using
    # the mapping specified below
    __metaclass__ = _HeaderMetaclass
    MDI = RealConstants.MDI
    CREATE_DIMS = (None, None)

    # The empty classmethod always produces a blank version of the object
    # of the correct (expected) size, filled with missing data indicators    
    @classmethod
    def empty(cls, num_cols=0, num_grids=0, word_size=DEFAULT_WORD_SIZE):
        if num_cols is None:
            num_cols = cls.CREATE_DIMS[0]
        if num_grids is None:
            num_grids = cls.CREATE_DIMS[1]
        if num_cols is None:
            raise(ValueError('"num_cols" has no valid default'))
        if num_grids is None:
            raise(ValueError('"num_grids" has no valid default'))
        reals = np.empty((num_cols, num_grids), dtype='>f{0}'.format(word_size))
        reals[:,:] = cls.MDI
        return cls(reals, word_size)

    # The from_file classmethod reads the header from a file object
    @classmethod
    def from_file(cls, source, num_cols, num_grids,
                  word_size=DEFAULT_WORD_SIZE):
        reals = np.fromfile(source, dtype='>f{0}'.format(word_size),
                            count=np.product((num_cols, num_grids)))
        reals = reals.reshape((num_cols, num_grids), order="F")
        return cls(reals, word_size)

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
        output_file.write(np.ravel(
            self._values[:,1:].astype('>f{0}'.format(word_size)), order="F"))

    @property
    def shape(self):
        return self._values[:, 1:].shape

    # This property enables access to the raw values in the array, in case
    # a user wishes to access them by index rather than by named attribute
    @property
    def raw(self):
        return self._values.view()

    def copy(self):
        return type(self)(self.raw[:,1:])

class UnsupportedHeaderItem1D(IntegerConstants):
    __metaclass__ = type
    CREATE_DIMS = (None,)

class UnsupportedHeaderItem2D(LevelDependentConstants):
    __metaclass__ = type
    CREATE_DIMS = (None, None)

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

    def to_file(self, output_file, word_size=DEFAULT_WORD_SIZE):
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
                   ('column_dependent_constants', ColumnDependentConstants),
                   ('fields_of_constants', UnsupportedHeaderItem2D),
                   ('extra_constants', UnsupportedHeaderItem1D),
                   ('temp_historyfile', UnsupportedHeaderItem1D),
                   ('compressed_field_index1', UnsupportedHeaderItem1D),
                   ('compressed_field_index2', UnsupportedHeaderItem1D),
                   ('compressed_field_index3', UnsupportedHeaderItem1D),
                   )  

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

    def copy(self, include_fields=False):
        """
        Make a copy of a UMFile object including all of its headers,
        and optionally also including copies of all of its fields.

        Kwargs:

        * include_fields:
            If True, the field list in the copied object will be populated
            with copies of the fields from the source object, otherwise the
            fields list in the new object will be empty

        """
        # Create a new object, with the same word size
        new_ffv = self.__class__(word_size=self._word_size)

        # Copy the fixed length header from the source FieldsFile
        new_ffv.fixed_length_header = self.fixed_length_header.copy()

        # Copy each other header component from the source FieldsFile
        for name, _ in self._COMPONENTS:
            component = getattr(self, name)
            if component is not None:
                setattr(new_ffv, name, component.copy())
            else:
                setattr(new_ffv, name, component)

        # Add a copy of the fields list if requested.
        if include_fields:
            new_ffv.fields = [field.copy() for field in self.fields]

        return new_ffv

    def __init__(self, word_size=None):
        """
        Create a UMFile instance.

        The initial creation contains an empty fixed-length-header, and
        any defined components for which the dimensions are fixed.

        Kwargs:

        * word_size:
            The number of bytes in each word.  Defaults to 8.

        """
        if word_size is None:
            word_size = DEFAULT_WORD_SIZE
        self._word_size = word_size
        self._source = None
        # source file
        self._source_path = None
        # source file path

        # Always create the output writing operators - these need to be
        # instantiated  and passed a reference to this object.
        # This is so the writers can access precalculated per-file information
        # (currently used for land and sea masks).
        self._write_operators = {}
        for lbpack_write in self._WRITE_OPERATORS.keys():
            self._write_operators[lbpack_write] = (
                self._WRITE_OPERATORS[lbpack_write](self))

        # Create an empty fixed length header.
        self.fixed_length_header = FixedLengthHeader.empty(word_size)

        # Add 'missing' components for all the required ones.
        for name, _ in self._COMPONENTS:
            setattr(self, name, None)

        # Note: initially has no no fields, no lookup.
        self.fields = []

    @classmethod
    def from_file(cls, file_or_filepath, word_size=None):
        """
        Initialise a UMFile, populated using the contents of a file

        Kwargs:

        * file_or_filepath:
            An open file-like object, or file path.
            A path is opened for read; a 'file-like' must support seeks.

        * word_size:
            The number of byte in each word.

        """
        new_ffv = cls(word_size=word_size)
        new_ffv._read_file(file_or_filepath)
        return new_ffv

    @classmethod
    def from_template(cls, template=None, word_size=None):
        """
        Create a fieldsfile from a template.

        The template is a dictionary of key:value, where 'key' is a component
        name and 'value' is a component settings dictionary.

        A component given a component settings dictionary in the template is
        guaranteed to exist in the resulting file object.

        Within a component dictionary, key:value pairs indicate the values that
        named component properties must be set to.

        If a component dictionary contains the special key 'dims', the
        associated value is a tuple of dimensions, which is passed to a
        component.empty() call to produce a new component of that type.

        .. for example::
            ffv = FieldsFile.from_template(
                'fixed_length_header':
                    {'dataset_type':3},  # set a particular header word
                'real_constants':
                    {},  # Add a standard-size 'real_constants' array
                'level_dependent_constants':
                    {'dims':(20,9)})  # add level-constants for 20 levels

        The resulting file is usually incomplete, but can be used as a
        convenient starting-point for creating files with a given structure.

        """
        new_ffv = cls(word_size=word_size)
        new_ffv._apply_template(template)
        return new_ffv

    def _read_file(self, file_or_filepath):
        if isinstance(file_or_filepath, basestring):
            self._source_path = file_or_filepath
            # If a filename is provided, open the file and populate the
            # fixed_length_header using its contents
            self._source = open(self._source_path, "rb")
        else:
            # Treat the argument as an open file.
            self._source = file_or_filepath
            self._source_path = file_or_filepath.name

        source = self._source
        word_size = self._word_size
        
        # Attach the fixed length header to the class
        self.fixed_length_header = (
            FixedLengthHeader.from_file(source, word_size))

        # Apply the appropriate headerclass from each component
        for name, headerclass in self._COMPONENTS:
            start = getattr(self.fixed_length_header, name+'_start')
            if start <= 0:
                continue
            if len(headerclass.CREATE_DIMS) == 1:
                length = getattr(self.fixed_length_header, name+'_length')
                header = headerclass.from_file(source, length, word_size)
            elif len(headerclass.CREATE_DIMS) == 2:
                dim1 = getattr(self.fixed_length_header, name+'_dim1')
                dim2 = getattr(self.fixed_length_header, name+'_dim2')
                header = headerclass.from_file(source, dim1, dim2, word_size)
                
            # Attach the component to the class
            setattr(self, name, header)

        # Now move onto reading in the lookup headers
        lookup_start = self.fixed_length_header.lookup_start
        if lookup_start > 0:
            source.seek((lookup_start - 1) * word_size)

            shape = (self.fixed_length_header.lookup_dim1,
                     self.fixed_length_header.lookup_dim2)

            lookup = np.fromfile(source,
                                 dtype='>i{0}'.format(word_size),
                                 count=np.product(shape))
            lookup = lookup.reshape(shape, order = "F")
        else:
            lookup = None

        # Read and add all the fields.
        self.fields = []
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
                reals = (raw_headers[self._FIELD.NUM_LOOKUP_INTS:]
                         .view(">f{0}".format(word_size)))
                field_class = self._FIELD_CLASSES.get(
                    ints[self._FIELD.LBREL_OFFSET], self._FIELD)
                if raw_headers[0] == -99:
                    provider = None
                else:
                    if is_model_dump:
                        offset = running_offset
                    else:
                        offset = (raw_headers[self._FIELD.LBEGIN_OFFSET] *
                                  word_size)
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
                self.fields.append(field)

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

    def _apply_template(self, template):
        """Apply the assignments specified in a template."""
        word_size=self._word_size
        for name, component_class in self._COMPONENTS:
            settings_dict = template.get(name)
            if settings_dict is not None:
                create_dims = settings_dict.pop('dims', [])
                component = getattr(self, name, None)
                if create_dims or component is None:
                    # Create a new component, or replace with given dimensions.
                    component = component_class.empty(*create_dims,
                                                      word_size=word_size)
                    # Install new component.
                    setattr(self, name, component)
                # Assign to specific properties of the component.
                for name, value in settings_dict.iteritems():
                    setattr(component, name, value)

    def __del__(self):
        if self._source and not self._source.closed:
            self._source.close()  

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
        """"
        Write all 'components' to the file, _except_ the fixed header.

        Also updates all the component location and dimension records in the
        fixed-length header.
        That is done here to ensure that these header words are in accord with
        the actual file locations.

        """
        # Go through each component defined for this file type
        for name, component_class in self._COMPONENTS:
            component = getattr(self, name)

            # Construct component position and shape info (or missing-values).
            file_word_position = int(output_file.tell() / self._word_size + 1)
            if component is not None:
                shape = component.shape
                ndims = len(shape)
            else:
                # Missing component : Use all-empty empty values.
                ndims = len(component_class.CREATE_DIMS)
                MDI = FixedLengthHeader.MDI
                shape = [MDI] * ndims
                file_word_position = MDI

            if ndims not in (1, 2):
                msg = 'Component type {} has {} dimensions, can not write.'
                raise ValueError(msg.format(name, ndims))


            # Record the position of this component in the fixed-length header.
            flh = self.fixed_length_header
            setattr(flh, name+'_start', file_word_position)

            # Record the component dimensions in the fixed-length header.
            if ndims == 1:
                setattr(flh, name+'_length', shape[0])
            elif ndims == 2:
                setattr(flh, name+'_dim1', shape[0])
                setattr(flh, name+'_dim2', shape[1])

            # Write out the component itself (if there is one).
            if component:
                component.to_file(output_file)

    def to_file(self, output_file_or_path):
        """
        Write to an output file or path.

        Args:

        * output_file_or_path (string or file-like):
            an open file or filepath.
            If a path, it is opened and closed afterwards.

        """
        if isinstance(output_file_or_path, basestring):
            with open(output_file_or_path, 'wb') as output_file:
                self._write_to_file(output_file)
        else:
            self._write_to_file(output_file_or_path)

    def _write_to_file(self, output_file):
        """Write out to an open output file."""
        # A reference to the header
        flh = self.fixed_length_header

        # Skip past the fixed length header for now
        output_file.seek(flh.NUM_WORDS * self._word_size)

        # Write out the singular headers (i.e. all headers apart from the
        # lookups, which will be done below).
        # This also updates all the fixed-length-header entries that specify
        # the position and size of the other header components.
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
                        # Can only do this if the LSM is packed in a way
                        # which this file object understands
                        lbpack321 = (field.lbpack -
                                     ((field.lbpack//1000) % 10)*1000)
                        if lbpack321 in self._WRITE_OPERATORS:
                            lsm = field.get_data().ravel()
                            self.land_mask = np.where(lsm == 1)[0]
                            self.sea_mask = np.where(lsm != 1)[0]

            # Write out all the field data payloads.
            for field in self.fields:
                if hasattr(field, 'HEADER_MAPPING'):

                    # Output 'recognised' lookup types (not blank entries).
                    field.lbegin = output_file.tell() / self._word_size

                    # WGDOS packed fields can be tagged with an accuracy of
                    # -99.0; this indicates that they should not be packed,
                    # so reset the packing code here accordingly
                    if field.lbpack % 10 == 1 and int(field.bacc) == -99:
                        field.lbpack = 10*(field.lbpack//10)

                    if field._can_copy_deferred_data(field.lbpack, field.bacc):
                        # The original, unread file data is encoded as wanted,
                        # so extract the raw bytes and write them back out
                        # again unchanged; however first trim off any existing
                        # padding to allow the code below to re-pad the output
                        data_bytes = field._get_raw_payload_bytes()
                        data_bytes = data_bytes[:field.lblrec*self._word_size]
                        output_file.write(data_bytes)
                    else:

                        # Strip just the n1-n3 digits from the lbpack value
                        # and check for a suitable write operator
                        lbpack321 = (field.lbpack -
                                     ((field.lbpack//1000) % 10)*1000)

                        if lbpack321 not in self._WRITE_OPERATORS:
                            msg = ('Cannot save data with lbpack={0} : '
                                   'packing not supported.')
                            raise ValueError(msg.format(field.lbpack))

                        data_bytes, data_size = (
                            self._write_operators[lbpack321].to_bytes(field))

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

            # Write out all the field lookups.
            for field in self.fields:
                field.to_file(output_file)

        # Write the fixed length header - now that we know how big
        # the DATA component was.
        output_file.seek(0)
        self.fixed_length_header.to_file(output_file)


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
    Load a UM file of undetermined type, by checking its dataset type and
    attempting to load it as the correct class.

    """
    def _load_umfile(file_path, open_file):
        flh = FixedLengthHeader.from_file(open_file)
        file_class = DATASET_TYPE_MAPPING.get(flh.dataset_type)
        if not file_class:
            msg = ("Unknown dataset_type {0}, supported types are {1}"
                   .format(flh.dataset_type, str(DATASET_TYPE_MAPPING.keys())))
            raise ValueError(msg)
        ffv_new = file_class.from_file(file_path)
        return ffv_new

    if isinstance(unknown_umfile, basestring):
        file_path = unknown_umfile
        with open(file_path) as open_file:
            result = _load_umfile(file_path, open_file)
    else:
        open_file = unknown_umfile
        file_path = open_file.name
        result = _load_umfile(file_path, open_file)

    return result
