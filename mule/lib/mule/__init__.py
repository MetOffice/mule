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
file formats produced and used by the UM (Unified Model) system.

The top-level :class:`UMFile` class provides an object representing a generic
UM file of the fieldsfile-like type, as covered in document UMDP F03.
This enables any file of this general form to be handled.

In practice, most files will be of a specific known subtype and it is then
simpler and safer to use the appropriate subclass, :class:`~mule.ff.FieldsFile`
or :class:`~mule.lbc.LBCFile` :  These perform type-specific sanity checking,
and provide named attributes to access all of the header elements.

for example:

>>> ff = mule.FieldsFile.from_file(in_path)
>>> print 'model = ', ff.fixed_length_header.model_version
>>> ff.integer_constants.num_soil_levels = 0
>>> ff.fields = [fld for fld in ff.fields
...              if (fld.lbuser7 == 1 and fld.lbuser4 in (204, 207)
                     and 1990 <= fld.lbyr < 2000)]
>>> ff.to_file(out_path)

The more general :class:`UMFile` class is provided to handle files of other
types, and can also be used to correct or adjust files of recognised types that
are invalid because of unexpected or inconsistent header information.

"""

from __future__ import (absolute_import, division, print_function)

import os
import numpy as np
import numpy.ma
import weakref
import six
from contextlib import contextmanager
from mule.stashmaster import STASHmaster

__version__ = "2022.07.1"

# UM fixed length header names and positions
_UM_FIXED_LENGTH_HEADER = [
    ('data_set_format_version',            1),
    ('sub_model',                          2),
    ('vert_coord_type',                    3),
    ('horiz_grid_type',                    4),
    ('dataset_type',                       5),
    ('run_identifier',                     6),
    ('experiment_number',                  7),
    ('calendar',                           8),
    ('grid_staggering',                    9),
    ('time_type',                         10),
    ('projection_number',                 11),
    ('model_version',                     12),
    ('obs_file_type',                     14),
    ('last_fieldop_type',                 15),
    ('t1_year',                           21),
    ('t1_month',                          22),
    ('t1_day',                            23),
    ('t1_hour',                           24),
    ('t1_minute',                         25),
    ('t1_second',                         26),
    ('t1_year_day_number',                27),
    ('t2_year',                           28),
    ('t2_month',                          29),
    ('t2_day',                            30),
    ('t2_hour',                           31),
    ('t2_minute',                         32),
    ('t2_second',                         33),
    ('t2_year_day_number',                34),
    ('t3_year',                           35),
    ('t3_month',                          36),
    ('t3_day',                            37),
    ('t3_hour',                           38),
    ('t3_minute',                         39),
    ('t3_second',                         40),
    ('t3_year_day_number',                41),
    ('integer_constants_start',          100),
    ('integer_constants_length',         101),
    ('real_constants_start',             105),
    ('real_constants_length',            106),
    ('level_dependent_constants_start',  110),
    ('level_dependent_constants_dim1',   111),
    ('level_dependent_constants_dim2',   112),
    ('row_dependent_constants_start',    115),
    ('row_dependent_constants_dim1',     116),
    ('row_dependent_constants_dim2',     117),
    ('column_dependent_constants_start', 120),
    ('column_dependent_constants_dim1',  121),
    ('column_dependent_constants_dim2',  122),
    ('additional_parameters_start',      125),
    ('additional_parameters_dim1',       126),
    ('additional_parameters_dim2',       127),
    ('extra_constants_start',            130),
    ('extra_constants_length',           131),
    ('temp_historyfile_start',           135),
    ('temp_historyfile_length',          136),
    ('compressed_field_index1_start',    140),
    ('compressed_field_index1_length',   141),
    ('compressed_field_index2_start',    142),
    ('compressed_field_index2_length',   143),
    ('compressed_field_index3_start',    144),
    ('compressed_field_index3_length',   145),
    ('lookup_start',                     150),
    ('lookup_dim1',                      151),
    ('lookup_dim2',                      152),
    ('total_prognostic_fields',          153),
    ('data_start',                       160),
    ('data_dim1',                        161),
    ('data_dim2',                        162),
    ]


# UM FieldsFile/PP LOOKUP header default class (contains the bare-minumum
# assumed elements for the purposes of associating the data and identifying
# the exact type of field).
_LOOKUP_HEADER_DEFAULT = [
    ('lblrec',  15),
    ('lbpack',  21),
    ('lbrel',   22),
    ('lbegin',  29),
    ('lbnrec',  30),
    ('bacc',    51),
    ]

# UM FieldsFile/PP LOOKUP header names and positions for header release vn.2
_LOOKUP_HEADER_2 = [
    ('lbyr',     1),
    ('lbmon',    2),
    ('lbdat',    3),
    ('lbhr',     4),
    ('lbmin',    5),
    ('lbday',    6),
    ('lbyrd',    7),
    ('lbmond',   8),
    ('lbdatd',   9),
    ('lbhrd',   10),
    ('lbmind',  11),
    ('lbdayd',  12),
    ('lbtim',   13),
    ('lbft',    14),
    ('lblrec',  15),
    ('lbcode',  16),
    ('lbhem',   17),
    ('lbrow',   18),
    ('lbnpt',   19),
    ('lbext',   20),
    ('lbpack',  21),
    ('lbrel',   22),
    ('lbfc',    23),
    ('lbcfc',   24),
    ('lbproc',  25),
    ('lbvc',    26),
    ('lbrvc',   27),
    ('lbexp',   28),
    ('lbegin',  29),
    ('lbnrec',  30),
    ('lbproj',  31),
    ('lbtyp',   32),
    ('lblev',   33),
    ('lbrsvd1', 34),
    ('lbrsvd2', 35),
    ('lbrsvd3', 36),
    ('lbrsvd4', 37),
    ('lbsrce',  38),
    ('lbuser1', 39),
    ('lbuser2', 40),
    ('lbuser3', 41),
    ('lbuser4', 42),
    ('lbuser5', 43),
    ('lbuser6', 44),
    ('lbuser7', 45),
    ('brsvd1',  46),
    ('brsvd2',  47),
    ('brsvd3',  48),
    ('brsvd4',  49),
    ('bdatum',  50),
    ('bacc',    51),
    ('blev',    52),
    ('brlev',   53),
    ('bhlev',   54),
    ('bhrlev',  55),
    ('bplat',   56),
    ('bplon',   57),
    ('bgor',    58),
    ('bzy',     59),
    ('bdy',     60),
    ('bzx',     61),
    ('bdx',     62),
    ('bmdi',    63),
    ('bmks',    64),
    ]

# UM FieldsFile/PP LOOKUP header names and positions for header release vn.3
# These are identical to header release vn.2 above apart from the 6th and 12th
# elements, which had their meanings changed from "day of year" to "second"
_LOOKUP_HEADER_3 = [(name, position) for name, position in _LOOKUP_HEADER_2]
_LOOKUP_HEADER_3[5] = ('lbsec', 6)
_LOOKUP_HEADER_3[11] = ('lbsecd', 12)

# Global default word (record) size (in bytes)
_DEFAULT_WORD_SIZE = 8

# Default missing values for **header** objects (not values in data!)
_INTEGER_MDI = -32768
_REAL_MDI = -1073741824.0


class _HeaderMetaclass(type):
    """
    Metaclass used to give named attributes to other classes.

    This metaclass is used in the construction of several header-like classes
    in this API; note that it is applied on *defining* the classes (i.e. when
    the module is imported), *not* later when a specific instance of the
    classes are initialised.

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

        The metaclass will assume the actual data values exist in an attribute
        of the target class called "_values".

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


class BaseHeaderComponent(six.with_metaclass(_HeaderMetaclass, object)):
    """
    Base class for a UM header component.

    .. Note::
        This class is not intended to be used directly; it acts only to
        group together the common parts of the :class:`BaseHeaderComponent1D`
        and :class:`BaseHeaderComponent2D` classes.

    """

    # The values in this base class should be overridden as they will
    # not do anything useful if left set to None.
    MDI = None
    """The value to use to indicate missing header values."""

    DTYPE = None
    """The data-type of the words in the header."""

    CREATE_DIMS = None
    """
    A tuple defining the default dimensions of the header to be produced
    by the :meth:`~BaseHeaderComponent.empty` method, when the caller provides
    incomplete shape information.
    Where an element of the tuple is "None", the arguments to the empty
    method *must* specify a size for the corresponding dimension.

    """

    HEADER_MAPPING = None
    """
    A list containing a series of tuple-pairs; the raw value of an index
    in the header, and a named-attribute to associate with it (see the help
    for the :class:`_HeaderMetaclass` for further details).

    """

    @property
    def shape(self):
        """Return the shape of the header object."""
        return self._values[..., 1:].shape

    @property
    def raw(self):
        """Return the raw values of the header object."""
        return self._values.view()

    def copy(self):
        """Create a copy of the header object."""
        return type(self)(self.raw[..., 1:])


class BaseHeaderComponent1D(BaseHeaderComponent):
    """1-Dimensional UM header component."""
    CREATE_DIMS = (None,)

    def __init__(self, values):
        """
        Initialise the object from a series of values.

        Args:
            * values:
                array-like object containing values in this header.

        .. Note::
            The values are internally stored offset by 1 element (so that
            when the raw values are accessed their indexing is 1-based, to
            match up with their definitions in UMDP F03).

        """
        self._values = np.empty(len(values) + 1, dtype=object)
        self._values[1:] = np.asarray(values, dtype=self.DTYPE)

    @classmethod
    def empty(cls, num_words=None):
        """
        Create an instance of the class from-scratch.

        Kwargs:
            * num_words:
                The number of words to use to create the header.

        .. Note::
            Passing "num_words" may be optional or mandatory depending
            on the value of the class's CREATE_DIMS attribute.

        """
        if num_words is None:
            num_words = cls.CREATE_DIMS[0]
        if num_words is None:
            raise(ValueError('"num_words" has no valid default'))
        return cls([cls.MDI]*num_words)

    @classmethod
    def from_file(cls, source, num_words):
        """
        Create an instance of the class populated by values from a file.

        Args:
            * source:
                The (open) file object containing the header value, with
                its file pointer positioned at the start of this header.
            * num_words:
                The number of words to read in from the file to populate
                the header.

        """
        values = np.fromfile(source, dtype=cls.DTYPE, count=num_words)
        return cls(values)

    def to_file(self, output_file):
        """
        Write the header to a file object.

        Args:
            * output_file:
                The (open) file object for the header to be written to.

        """
        output_file.write(self._values[1:].astype(self.DTYPE))


class BaseHeaderComponent2D(BaseHeaderComponent):
    """2-Dimensional UM header component."""
    CREATE_DIMS = (None, None)

    def __init__(self, values):
        """
        Initialise the object from a series of values.

        Args:
            * values:
                2-dimensional array-like object containing values in
                this header.

        .. Note::
            The values are internally stored offset by 1 element in their
            second dimension (so that when the raw values are accessed their
            indexing is 1-based, to match up with the definitions in UMDP F03).

        """
        self._values = np.empty((values.shape[0], values.shape[1] + 1),
                                dtype=object)
        self._values[:, 1:] = values

    @classmethod
    def empty(cls, dim1=None, dim2=None):
        """
        Create an instance of the class from-scratch.

        Kwargs:
            * dim1:
                The number of words to use for the header's first dimension.
            * dim2:
                The number of words to use for the header's second dimension.

        .. Note::
            Setting "dim1" and/or "dim2" may be optional or mandatory
            depending on the values of the class's CREATE_DIMS attribute.

        """
        if dim1 is None:
            dim1 = cls.CREATE_DIMS[0]
        if dim2 is None:
            dim2 = cls.CREATE_DIMS[1]
        if dim1 is None:
            raise(ValueError('"dim1" has no valid default'))
        if dim2 is None:
            raise(ValueError('"dim2" has no valid default'))
        values = np.empty((dim1, dim2), dtype=cls.DTYPE)
        values[:, :] = cls.MDI
        return cls(values)

    @classmethod
    def from_file(cls, source, dim1, dim2):
        """
        Create an instance of the class populated by values from a file.

        Args:
            * source:
                The (open) file object containing the header value, with
                its file pointer positioned at the start of this header.
            * dim1:
                The number of words to read in from the file to populate
                each row of the header.
            * dim2:
                The number of the above rows to read in from the file to
                populate the header.

        """
        values = np.fromfile(source, dtype=cls.DTYPE,
                             count=np.product((dim1, dim2)))
        values = values.reshape((dim1, dim2), order="F")
        return cls(values)

    def to_file(self, output_file):
        """
        Write the header to a file object.

        Args:
            * output_file:
                The (open) file object for the header to be written to.

        """
        output_file.write(np.ravel(
            self._values[:, 1:].astype(self.DTYPE), order="F"))


class FixedLengthHeader(BaseHeaderComponent1D):
    """
    The fixed length header component of a UM file.

    This component is different to the others since its length is not
    able to be altered at creation-time; the fixed length header is
    always a specific number of words in length.

    """
    HEADER_MAPPING = _UM_FIXED_LENGTH_HEADER
    MDI = _INTEGER_MDI
    DTYPE = ">i8"

    _NUM_WORDS = 256
    """The (fixed) number of words in a UM fixed length header."""

    def __init__(self, values):
        """
        Initialise the object from a series of values.

        Args:
            * values:
                array-like object containing values contained in this header.
                Must be the exact length specified by _NUM_WORDS.

        .. Note::
            The values are internally stored offset by 1 element (so that
            when the raw values are accessed their indexing is 1-based, to
            match up with their definitions in UMDP F03).

        """
        if len(values) != self._NUM_WORDS:
            _msg = ('Incorrect size for fixed length header; given {0} words '
                    'but should be {1}.'.format(len(values), self._NUM_WORDS))
            raise ValueError(_msg)
        super(FixedLengthHeader, self).__init__(values)

    @classmethod
    def empty(cls):
        """
        Create an instance of the class from-scratch.

        Unlike the other header components the fixed length header always
        creates a class of a fixed size (based on its _NUM_WORDS attribute).

        """
        return super(FixedLengthHeader, cls).empty(cls._NUM_WORDS)

    @classmethod
    def from_file(cls, source):
        """
        Create an instance of the class populated by values from a file.

        Unlike the other header components the fixed length header always
        reads a specific number of values (based on its _NUM_WORDS attribute).

        Args:
            * source:
                The (open) file object containing the header value, with
                its file pointer positioned at the start of this header.

        """
        return super(FixedLengthHeader, cls).from_file(source, cls._NUM_WORDS)


class IntegerConstants(BaseHeaderComponent1D):
    """The integer constants component of a UM file."""
    MDI = _INTEGER_MDI
    DTYPE = ">i8"


class RealConstants(BaseHeaderComponent1D):
    """The real constants component of a UM file."""
    MDI = _REAL_MDI
    DTYPE = ">f8"


class LevelDependentConstants(BaseHeaderComponent2D):
    """The level dependent constants component of a UM file."""
    MDI = _REAL_MDI
    DTYPE = ">f8"


class RowDependentConstants(BaseHeaderComponent2D):
    """The row dependent constants component of a UM file."""
    MDI = _REAL_MDI
    DTYPE = ">f8"


class ColumnDependentConstants(BaseHeaderComponent2D):
    """The column dependent constants component of a UM file."""
    MDI = _REAL_MDI
    DTYPE = ">f8"


class UnsupportedHeaderItem1D(BaseHeaderComponent1D):
    """An unsupported 1-dimensional component of a UM file."""
    __metaclass__ = type

    MDI = _INTEGER_MDI
    DTYPE = ">i8"


class UnsupportedHeaderItem2D(BaseHeaderComponent2D):
    """An unsupported 2-dimensional component of a UM file."""
    __metaclass__ = type

    MDI = _INTEGER_MDI
    DTYPE = ">i8"


class Field(six.with_metaclass(_HeaderMetaclass, object)):
    """
    Represents a single entry in the lookup table, and provides access to
    the data referenced by it.

    .. Note::
        This class assumes the (common) UM lookup header comprising of
        64 words split between 45 integer and 19 real values.

    """
    HEADER_MAPPING = _LOOKUP_HEADER_DEFAULT

    # The expected number of lookup entries which are integers and reals.
    NUM_LOOKUP_INTS = 45
    NUM_LOOKUP_REALS = 19

    # The types of the integers and reals.
    DTYPE_INT = ">i8"
    DTYPE_REAL = ">f8"

    def __init__(self, int_headers, real_headers, data_provider):
        """
        Initialise the Field object.

        Args:
            * int_headers:
                A sequence of integer header values.
            * real_headers:
                A sequence of floating-point header values.
            * data_provider:
                An object representing the field data payload.
                Typically, this is an object with a "._data_array" method,
                in which case the data can be fetched with :meth:`get_data`.

        """
        # Create a numpy object array to hold the entire lookup, leaving a
        # space for the zeroth index so that it behaves like the 1-based
        # indexing referred to in UMDP F03
        self._values = np.ndarray(len(int_headers) + len(real_headers) + 1,
                                  dtype=object)

        # Populate the first half with the integers
        self._values[1:len(int_headers)+1] = (
            np.asarray(int_headers, dtype=self.DTYPE_INT))
        # And the rest with the real values
        self._values[len(int_headers)+1:] = (
            np.asarray(real_headers, dtype=self.DTYPE_REAL))

        # Create views onto the above array to retrieve the integer/real
        # parts of the lookup header separately (for writing out)
        self._lookup_ints = self._values[1:len(int_headers)+1]
        self._lookup_reals = self._values[len(int_headers)+1:]

        # Save the reference to the given data provider.
        self._data_provider = data_provider

        # Initialise an empty stash entry (this may optionally be set by
        # the containing file object later on)
        self.stash = None

    @classmethod
    def empty(cls):
        """
        Create an instance of the class from-scratch.

        The instance will be filled with empty values (-99 for integers,
        and 0.0 for reals), and will have no data_provider set.

        """
        integers = np.empty(cls.NUM_LOOKUP_INTS, cls.DTYPE_INT)
        integers[:] = -99
        reals = np.empty(cls.NUM_LOOKUP_REALS, cls.DTYPE_REAL)
        reals[:] = 0.0

        return cls(integers, reals, None)

    @property
    def raw(self):
        """Return the raw values in the lookup array."""
        return self._values.view()

    def to_file(self, output_file):
        """
        Write the lookup header to a file object.

        Args:
            * output_file:
                The (open) file object for the lookup to be written to.

        """
        output_file.write(self._lookup_ints.astype(self.DTYPE_INT))
        output_file.write(self._lookup_reals.astype(self.DTYPE_REAL))

    def copy(self):
        """
        Create a Field which copies its header information from this one, and
        takes its data from the same data provider.

        """
        new_field = type(self)(self._lookup_ints.copy(),
                               self._lookup_reals.copy(),
                               self._data_provider)
        new_field.stash = self.stash
        return new_field

    def set_data_provider(self, data_provider):
        """
        Set the field data payload.

        Args:
            * data_provider:
                An object representing the field data payload.
                Typically, this is an object with a "._data_array" method,
                which means the data can be accessed with :meth:`get_data`.

        """
        self._data_provider = data_provider

    def num_values(self):
        """Return the number of values defined by this header."""
        return len(self._values) - 1

    def get_data(self):
        """Return the data for this field as an array."""
        data = None
        if hasattr(self._data_provider, '_data_array'):
            data = self._data_provider._data_array()
        return data

    def _get_raw_payload_bytes(self):
        """
        Return a buffer containing the raw bytes of the data payload.

        The field data must be unmodified and using the same packing
        code as the original data (this can be tested by calling
        _can_copy_deferred_data).

        """
        data = None
        if hasattr(self._data_provider, "_read_bytes"):
            data = self._data_provider._read_bytes()
        return data

    def _can_copy_deferred_data(self, required_lbpack, required_bacc,
                                required_word):
        """
        Return whether or not it is possible to simply re-use the bytes
        making up the field; for this to be possible the data must be
        unmodified, and the requested output packing and disk word size must
        be the same as the input.

        """
        # Whether or not this is possible depends on if the Field's
        # data provider has been wrapped in any operations
        compatible = hasattr(self._data_provider, "_read_bytes")
        if compatible:
            # Is the packing code the same
            src_lbpack = self._data_provider.source.lbpack
            compatible = required_lbpack == src_lbpack

            # If it's WGDOS packing, the accuracy matters too
            if src_lbpack == 1:
                src_bacc = self._data_provider.source.bacc
                compatible = compatible and required_bacc == src_bacc
            else:
                # Otherwise the disk size matters
                src_word = self._data_provider.DISK_RECORD_SIZE
                compatible = compatible and required_word == src_word

        return compatible


class Field2(Field):
    """
    Represents an entry from the LOOKUP component with a header release
    number of 2.

    """
    HEADER_MAPPING = _LOOKUP_HEADER_2


class Field3(Field):
    """
    Represents an entry from the LOOKUP component with a header release
    number of 3.

    """
    HEADER_MAPPING = _LOOKUP_HEADER_3


class ArrayDataProvider(object):
    """
    A :class:`Field` data provider that contains an actual array of values.

    This is used to make a field with an ordinary array as its data payload.

    .. Note::

        This must be used with caution, as multiple fields with a concrete data
        payload can easily consume large amounts of space.
        By contrast, processing field payloads from an existing file will
        normally only load one at a time.

    """
    def __init__(self, array):
        """
        Create a data-provider which contains a concrete data array.

        Args:
            * array (array-like):
                The data payload.  It is converted to a numpy array.
                It must be 2D unmasked data.

        """
        if numpy.ma.is_masked(array):
            raise ValueError('ArrayDataProvider does not handle masked data.')
        array = numpy.asarray(array)
        shape = array.shape
        if len(shape) != 2:
            msg = 'ArrayDataProvider has shape {}, which is not 2-dimensional.'
            raise ValueError(msg.format(shape))
        self._array = array

    def _data_array(self):
        """Return the data payload."""
        return self._array


class _OperatorDataProvider(object):
    """
    A :class:`Field` data provider that fetches its data from a
    :class:`DataOperator`, by calling :meth:`transform`.

    ..Note: This should only really ever be instantiated from within
            the :class:`DataOperator`.

    """
    def __init__(self, operator, source, new_field):
        """
        Create a wrapper, including references to the operator,
        the original source data and and the result field.

        Args:
            * operator:
                A reference to the :class:`DataOperator` instance which
                created this provider (to allow its :meth:`transform`
                method to be accessed in :meth:`_data_array` below).
            * source:
                The source object for the above :class:`DataOperator` -
                this can be anything, and is required here so that it can
                be passed onto the operator's meth:`transform` method below.
            * new_field:
                The new field returned by the above :class:`DataOperator` -
                this is again needed by the operator's meth:`transform` method.

        """
        self.operator = operator
        self.source = source
        # The reference which is passed to the transform below must be a
        # weakref.  The reason for this is to avoid a circular dependency
        # that will interfere with Python's garbage collection.  Since the
        # operator will ultimately be attached to the new_field object, it
        # *must not* hold a reference to it as well.
        self.result_field = weakref.ref(new_field)

    def _data_array(self):
        """Return the data using the provided operator."""
        return self.operator.transform(self.source, self.result_field)


class DataOperator(object):
    """
    Base class which should be sub-classed to perform manipulations on the
    data of a field.  The :class:`Field` classes never store any data directly
    in memory; only the means to retrieve it from disk and perform any required
    operations (which will only be executed when explicitly requested - this
    would normally be at the point the file is being written/closed).

    .. Note::
        the user must override the "__init__", "new_field" and "transform"
        methods of this baseclass to create a valid operator.

    A DataOperator is used to produce new :class:`Field` s, which are
    calculated from existing source fields and which can also calculate their
    data results from the source data at a subsequent time.

    The normal usage occurs in 3 separate stages:

      *   :meth:`__init__` creates a new operator with any instance-specific
          parameters.
      *   :meth:`__call__` is used to produce a new, transformed :class:`Field`
          objects from existing ones, via the user :meth:`new_field` method.
      *   :meth:`transform` is called by an output field to calculate its data
          payload.

    For example:

    >>> class XSampler(DataOperator):
    ...     def __init__(self, factor):
    ...         self.factor = factor
    ...     def new_field(self, source_field):
    ...         fld = source_field.copy()
    ...         fld.lbnpt /= self.factor
    ...         fld.bdx *= self.factor
    ...         return fld
    ...     def transform(self, source_field, result_field):
    ...         data = source_field.get_data()
    ...         return data[:, ::self.factor]
    ...
    >>> XStep4 = XSampler(factor=4)
    >>> ff.fields = [XStep4(fld) for fld in ff.fields]
    >>> ff.to_file(out_path)

    """

    def __init__(self, *args, **kwargs):
        """
        Initialise the operator object - this should be overridden by the user.

        This method should accept any user arguments to be "baked" into the
        operator or to otherwise initialise it as-per the user's requirements;
        for example an operator which scales the values in fields by a
        constant amount might want to accept an argument giving that amount.

        """
        msg = ("The __init__ method of the DataOperator baseclass should be "
               "overridden by the user")
        raise NotImplementedError(msg)

    def __call__(self, source, *args, **kwargs):
        """
        Wrap the operator around a source object.

        This calls the user-supplied :meth:`new_field` method, and configures
        the resulting field to return its data from the :meth:`transform`
        method of the data operator.

        Args:
            * source:
                This can be an object of any type; it is typically an existing
                :class:`Field` which the result field is based on.

        Returns:
            * new_field (:class:`Field`):
                A new Field instance, which returns data generated via the
                :meth:`transform` method.

        """
        new_field = self.new_field(source, *args, **kwargs)
        provider = _OperatorDataProvider(self, source, new_field)
        new_field.set_data_provider(provider)
        return new_field

    def new_field(self, source, *args, **kwargs):
        """
        Produce a new output :class:`Field` from a source object
        - this method should be overridden by the user.

        This method encodes how to produce a new field, which is typically
        derived by calculation from an existing source field or fields.
        It is called by the :meth:`__call__` method.

        Args:
            * source:
                This can be an object of any type; it is typically an existing
                :class:`Field` which the result field is based on.

        Returns:
            * new_field (:class:`Field`):
                A new Field instance, whose lookup attributes reflect the final
                state of the result:
                E.G. if the operator affects the number of rows in the field,
                then 'new_field' must have its row settings set accordingly.

        .. Note::
            It is advisable not to modify the "source" object inside this
            method; modifications should be confined to the new field object.

        """
        msg = ("The new_field method of the DataOperator baseclass should be "
               "overridden by the user")
        raise NotImplementedError(msg)

    def transform(self, source, result_field):
        """
        Calculate the data payload for a result field
        - this method should be overridden by the user.

        This method must return a 2D numpy array containing the field data.
        Typically it will extract the data payload from a source field and
        manipulate it in some way.

        Args:
            * source:
                The original 'source' argument from the :meth:`__call__`
                invocation that created 'result_field'.
                Usually, this is a pre-existing :class:`Field` object from
                which the result field is calculated.

            * result_field:
                The 'new' field that was created by a call to :meth:`__call__`,
                for which the data is now wanted.
                This should not be modified, but provides access to any
                necessary context information determined when it was created.

        Returns:
            * data (array):
                The data array for 'result_field'.

        """
        msg = ("The transform method of the DataOperator baseclass should be "
               "overridden by the user")
        raise NotImplementedError(msg)


class RawReadProvider(object):
    """
    A generic 'data provider' object, which deals with the most basic/common
    data-provision operation of reading in Field data from a file.

    This class should not be used directly, since it does not define a
    "_data_array" method, and so cannot return any data.
    A series of subclasses of this class are provided which define the
    '_data_array' method for the different packing types found in various
    types of :class:`UMFile`.

    """
    DISK_RECORD_SIZE = _DEFAULT_WORD_SIZE

    def __init__(self, source, sourcefile, offset):
        """
        Initialise the read provider.

        Args:
            * source:
                Initial field object reference (populated with the lookup
                values from the file specified in sourcefile.
            * sourcefile:
                Filename associated with source FieldsFileVariant.
            * offset:
                Starting position of Field data in sourcefile (in bytes).

        """
        self.source = source
        self.sourcefile = sourcefile
        self.offset = offset

    @contextmanager
    def _with_source(self):
        # Context manager to temporarily reopen the sourcefile if the original
        # provided at create time has been closed.
        reopen_required = self.sourcefile.closed
        close_required = False
        try:
            if reopen_required:
                self.sourcefile = open(self.sourcefile.name, "rb")
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
            data_size = field.lbnrec * self.DISK_RECORD_SIZE
            data_bytes = self.sourcefile.read(data_size)
        return data_bytes


class _NullReadProvider(RawReadProvider):
    """
    A 'raw' data provider object to be used when a packing code is unrecognised
    - to be able to represent unknown-type data in a :class:`Field`.

    """
    def _data_array(self):
        lbpack = self.source.raw[21]
        msg = "Packing code {0} unsupported".format(lbpack)
        raise NotImplementedError(msg)


class UMFile(object):
    """Represents the structure of a single UM file."""

    # The base UMFile object uses the base versions of the standard components,
    # these will allow any shape for each component, and do not have associated
    # mappings for the values (so they will not have nicely named properties).
    COMPONENTS = (('integer_constants', IntegerConstants),
                  ('real_constants', RealConstants),
                  ('level_dependent_constants', LevelDependentConstants),
                  ('row_dependent_constants', RowDependentConstants),
                  ('column_dependent_constants', ColumnDependentConstants),
                  ('additional_parameters', UnsupportedHeaderItem2D),
                  ('extra_constants', UnsupportedHeaderItem1D),
                  ('temp_historyfile', UnsupportedHeaderItem1D),
                  ('compressed_field_index1', UnsupportedHeaderItem1D),
                  ('compressed_field_index2', UnsupportedHeaderItem1D),
                  ('compressed_field_index3', UnsupportedHeaderItem1D),
                  )
    """
    A series of tuples containing the name of a header component, and the
    class which should be used to represent it.  The name  will become the
    final attribute name to store the component, but it must also correspond
    to a name in the HEADER_MAPPING of the fixed length header.

    """

    # The base UMFile object does not provide any read or write operators,
    # since these depend on the specific type of file.  Therefore this base
    # class can only "pass-through" field data; it can't change the values or
    # the packing used for any of the fields.
    READ_PROVIDERS = {}
    """
    A dictionary which maps a string containing the trailing 3 digits
    (n3 - n1) of a field's lbpack (packing code) onto a suitable
    data-provider object to read the field.  Any packing code not in
    this list will default to using a :class:`_NullReadProvider` object
    (which can only be used to copy the raw byte-data of the field -
    not to unpack it or access the data).

    """

    WRITE_OPERATORS = {}
    """
    A dictionary which maps a string containing the trailing 3 digits
    (n3 - n1) of a field's lbpack (packing code) onto a suitable
    :class:`DataOperator` object to write the field.  Any packing code
    found in a field from this object's field list but not found here
    will cause an exception when trying to write to a file.

    """

    WORD_SIZE = _DEFAULT_WORD_SIZE
    """
    The word/record size for the file, for all supported UM file types this
    should be left as the default - 8 (i.e. 64-bit words).

    """

    # As well as setting the default release Field classes to use, a reference
    # is required to an unknown version of the Field class - to assist in the
    # initial reading of an unknown field.
    FIELD_CLASSES = {2: Field2, 3: Field3, -99: Field}
    """
    Maps the lblrel (header release number) of each field onto an appropriate
    :class:`Field` subclass to represent it.

    .. Note::
        This mapping *must* contain an entry for -99, and the :class:`Field`
        object it returns *must* at a minimum contain attribute mappings for
        the 5 key elements (lbrel, lblrec, lbnrec, lbegin and lbpack - see
        UMDP F03), as well as suitable shape information.

    """

    # Data alignment values (to match with UM definitions).
    _WORDS_PER_SECTOR = 512         # Padding for each field (in words).
    _DATA_START_ALIGNMENT = 524288  # Padding to start of data (in bytes).

    def __init__(self):
        """
        Create a blank UMFile instance.

        The initial creation contains only an empty :class:`FixedLengthHeader`
        object, plus an empty (None) named attribute for each component in
        the COMPONENTS attribute.

        In most cases this __init__ should not be called directly, but
        indirectly via the from_file or from_template classmethods.

        """
        self._source = None
        self._source_path = None

        # At the class definition level, WRITE_OPERATORS is a mapping onto the
        # write operator classes.  Before these can be used to output data
        # they need to be instantiated; the instances are then re-attached to
        # WRITE_OPERATORS to be called upon later.
        self._write_operators = {}
        for lbpack_write in self.WRITE_OPERATORS.keys():
            self._write_operators[lbpack_write] = (
                self.WRITE_OPERATORS[lbpack_write]())

        # Attach an empty fixed length header
        self.fixed_length_header = FixedLengthHeader.empty()

        # Add a blank entry for each required component.
        for name, _ in self.COMPONENTS:
            setattr(self, name, None)

        # Add a blank entry for the associated stashmaster
        self.stashmaster = None

        # Initialise the field list.
        self.fields = []

    def __del__(self):
        """
        Ensure any associated file is closed if this object goes out of scope.

        """
        if self._source and not self._source.closed:
            self._source.close()

    def __str__(self):
        items = []
        for name, kind in self.COMPONENTS:
            value = getattr(self, name)
            if value is not None:
                items.append('{0}={1}'.format(name, value.shape))
        if self.fields:
            items.append('fields={0}'.format(len(self.fields)))
        return '<{0}: {1}>'.format(type(self).__name__, ', '.join(items))

    def __repr__(self):
        fmt = '<{0}: fields={1}>'
        return fmt.format(type(self).__name__, len(self.fields))

    @classmethod
    def from_file(cls, file_or_filepath, remove_empty_lookups=False,
                  stashmaster=None):
        """
        Initialise a UMFile, populated using the contents of a file.

        Kwargs:
            * file_or_filepath:
                An open file-like object, or file path.
                A path is opened for read; a 'file-like' must support seeks.
            * remove_empty_lookups:
                If set to True, will remove any "empty" lookup headers from
                the field-list (UM files often have pre-allocated numbers
                of lookup entries, some of which are left unused).
            * stashmaster:
                A :class:`mule.stashmaster.STASHMaster` object containing
                the details of the STASHmaster to associate with the fields
                in the file (if not provided will attempt to load a central
                STASHmaster based on the version in the fixed length header).

        .. Note::
            As part of this the "validate" method will be called. For the
            base :class:`UMFile` class this does nothing, but sub-classes
            may override it to provide specific validation checks.

        """
        # First create the class and then populate it from the file.
        new_umf = cls()
        new_umf._read_file(file_or_filepath)

        if remove_empty_lookups:
            new_umf.remove_empty_lookups()

        # Try to attach STASH entries to the fields, using the STASHmaster
        # associated with the model version found in the header (note that
        # this doesn't work for ancillary files)
        if stashmaster is not None:
            new_umf.attach_stashmaster_info(stashmaster)
        else:
            stashmaster = STASHmaster.from_umfile(new_umf)
            if stashmaster is not None:
                new_umf.attach_stashmaster_info(stashmaster)

        # Validate the new object, to check it has been created properly
        new_umf.validate(filename=new_umf._source_path, warn=True)

        return new_umf

    @classmethod
    def from_template(cls, template=None):
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
        Note that in some cases "None" may be used to indicate a dimension
        which the file-type fixes (e.g. the number of level types).

        .. for example::
            ff = FieldsFile.from_template(
                'fixed_length_header':
                    {'dataset_type':3},  # set a particular header word
                'real_constants':
                    {},  # Add a standard-size 'real_constants' array
                'level_dependent_constants':
                    {'dims':(20, None)})  # add level-constants for 20 levels

        The resulting file is usually incomplete, but can be used as a
        convenient starting-point for creating files with a given structure.

        .. Note::
            When a particular component contains known values in any position
            of its "CREATE_DIMS" attribute (i.e. not "None"), the template
            may omit this dimension (as is done in the example above for the
            'level_dependent_constants' 2nd dimension.

        """
        # First create the class and then populate it from the template.
        new_umf = cls()
        new_umf._apply_template(template)
        return new_umf

    def attach_stashmaster_info(self, stashmaster):
        """
        Attach references to the relevant entries in a provided
        :class:mule.stashmaster.STASHmaster object to each of the fields
        in this object.

        Args:
            * stashmaster:
                A :class:mule.stashmaster.STASHmaster instance which should
                be parsed and attached to any fields in the file.

        """
        self.stashmaster = stashmaster
        for field in self.fields:
            if hasattr(field, "lbuser4") and field.lbuser4 in stashmaster:
                field.stash = stashmaster[field.lbuser4]
            else:
                field.stash = None

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
        new_umf = self.__class__()
        new_umf.fixed_length_header = self.fixed_length_header.copy()

        for name, _ in self.COMPONENTS:
            component = getattr(self, name)
            if component is not None:
                setattr(new_umf, name, component.copy())
            else:
                setattr(new_umf, name, component)

        new_umf.stashmaster = self.stashmaster

        if include_fields:
            new_umf.fields = [field.copy() for field in self.fields]

        return new_umf

    def validate(self, filename=None, warn=False):
        """
        Apply any consistency checks to check the file is "valid".

        .. Note::
            In the base :class:`UMFile` class this routine does nothing but
            a format-specific subclass can override this method to do whatever
            it considers appropriate to validate the file object.

        """
        pass

    def remove_empty_lookups(self):
        """
        Calling this method will delete any fields from the field list
        which are empty.

        """
        self.fields = [field for field in self.fields
                       if field.raw[1] != -99]

    def to_file(self, output_file_or_path):
        """
        Write to an output file or path.

        Args:
            * output_file_or_path (string or file-like):
                An open file or filepath. If a path, it is opened and
                closed again afterwards.

        .. Note::
            As part of this the "validate" method will be called. For the
            base :class:`UMFile` class this does nothing, but sub-classes
            may override it to provide specific validation checks.

        """
        # Call validate - to ensure the file about to be written out doesn't
        # contain obvious errors.  This is done here before any new file is
        # created so that we don't create a blank file if the validation fails
        if isinstance(output_file_or_path, six.string_types):
            self.validate(filename=output_file_or_path)
        else:
            self.validate(filename=output_file_or_path.name)

        if isinstance(output_file_or_path, six.string_types):
            with open(output_file_or_path, 'wb') as output_file:
                self._write_to_file(output_file)
        else:
            self._write_to_file(output_file_or_path)

    def _read_file(self, file_or_filepath):
        """Populate the class from an existing file object or file"""
        if isinstance(file_or_filepath, six.string_types):
            self._source_path = file_or_filepath
            # If a filename is provided, open the file and populate the
            # fixed_length_header using its contents
            self._source = open(self._source_path, "rb")
        else:
            # Treat the argument as an open file.
            self._source = file_or_filepath
            self._source_path = file_or_filepath.name

        source = self._source

        # Attach the fixed length header to the class
        self.fixed_length_header = (
            FixedLengthHeader.from_file(source))

        # Apply the appropriate headerclass from each component
        for name, headerclass in self.COMPONENTS:
            start = getattr(self.fixed_length_header, name+'_start')
            if start <= 0:
                continue
            if len(headerclass.CREATE_DIMS) == 1:
                length = getattr(self.fixed_length_header, name+'_length')
                header = headerclass.from_file(source, length)
            elif len(headerclass.CREATE_DIMS) == 2:
                dim1 = getattr(self.fixed_length_header, name+'_dim1')
                dim2 = getattr(self.fixed_length_header, name+'_dim2')
                header = headerclass.from_file(source, dim1, dim2)

            # Attach the component to the class
            setattr(self, name, header)

        # Now move onto reading in the lookup headers.
        lookup_start = self.fixed_length_header.lookup_start
        if lookup_start > 0:
            source.seek((lookup_start - 1) * self.WORD_SIZE)

            shape = (self.fixed_length_header.lookup_dim1,
                     self.fixed_length_header.lookup_dim2)

            lookup = np.fromfile(source,
                                 dtype='>i{0}'.format(self.WORD_SIZE),
                                 count=np.product(shape))
            # Catch if the file has no lookups/data to read
            if len(lookup) > 0:
                lookup = lookup.reshape(shape, order="F")
            else:
                lookup = None
        else:
            lookup = None

        # Read and add all the fields.
        self.fields = []
        if lookup is not None:
            # A quick helper function to create the default field class
            # from a part of the raw array
            default_field_class = self.FIELD_CLASSES[-99]

            def default_from_raw(values):
                ints = values[:default_field_class.NUM_LOOKUP_INTS]
                reals = (values[default_field_class.NUM_LOOKUP_INTS:]
                         .view(default_field_class.DTYPE_REAL))
                return default_field_class(ints, reals, None)

            # Setup the first field, and check if it is using well-formed
            # records (i.e. the header defines the position of the field).
            first_field = default_from_raw(lookup.T[0])
            is_well_formed = (first_field.lbnrec != 0 and
                              first_field.lbegin != 0)
            if not is_well_formed:
                # If the file is not well formed, keep a running offset.
                running_offset = ((self.fixed_length_header.data_start - 1) *
                                  self.WORD_SIZE)

            for raw_headers in lookup.T:
                # Populate the default field class first - for now we only
                # need the minimum information about the field.
                default_field = default_from_raw(raw_headers)

                # Lookup what the final class for the field should be
                # (based on its release version).
                field_class = self.FIELD_CLASSES.get(
                    default_field.lbrel, self.FIELD_CLASSES[-99])

                # Update the field to the correct Field subclass.
                field = field_class(default_field._lookup_ints,
                                    default_field._lookup_reals,
                                    None)

                # Attach an appropriate data provider (unless the field is
                # empty - in which case it doesn't need a provider).
                if raw_headers[0] == -99:
                    provider = None
                else:
                    # Update the running offset if needed.
                    if not is_well_formed:
                        offset = running_offset
                    else:
                        offset = field.lbegin*self.WORD_SIZE

                    # Now select which type of basic reading and unpacking
                    # provider is suitable for the type of file and data,
                    # starting by checking the number format (N4 position)
                    num_format = (field.lbpack//1000) % 10
                    # Check number format is valid
                    if num_format not in (0, 2, 3):
                        msg = 'Unsupported number format (lbpack N4): {0}'
                        raise ValueError(msg.format(num_format))

                    # With that check out of the way remove the N4 digit and
                    # proceed with the N1 - N3 digits
                    lbpack321 = field.lbpack - num_format*1000

                    # Select an appropriate read provider for this packing
                    # code if one is available, otherwise use the default
                    # provider (which cannot actually decode the data)
                    read_provider = (
                        self.READ_PROVIDERS.get(
                            "{0:03d}".format(lbpack321),
                            _NullReadProvider))

                    # Create the provider, passing a reference to the field,
                    # the file object and the start position to read the data
                    # (Note that we pass a copy of the field, not the original
                    # - this is because we *do not* want that reference to be
                    # modified; since it will be needed to read the data).
                    provider = read_provider(field.copy(), source, offset)

                # Now attach the selected provider to the field object and
                # add it to the field-list
                field.set_data_provider(provider)
                self.fields.append(field)

                # Update the running offset if required
                if not is_well_formed:
                    running_offset += field.lblrec*self.WORD_SIZE

    def _apply_template(self, template):
        """Apply the assignments specified in a template."""
        # Apply changes to fixed-length-header and components, *in that order*
        # Note: flh *always* exists, so can safely add it to the list of
        # components with a "None" class.
        all_headers = [('fixed_length_header', None)] + list(self.COMPONENTS)

        # Take a copy of the template and remove elements as they are set
        template = template.copy()
        for component_name, component_class in all_headers:
            settings_dict = template.pop(component_name, None)
            if settings_dict is not None:
                create_dims = settings_dict.pop('dims', [])
                component = getattr(self, component_name, None)
                if create_dims or component is None:
                    # Create a new component, or replace with given dimensions.
                    component = component_class.empty(*create_dims)

                    # Install new component.
                    setattr(self, component_name, component)
                # Assign to specific properties of the component.
                for item_name, value in six.iteritems(settings_dict):
                    if not hasattr(component, item_name):
                        msg = ('File header component "{0}" '
                               'has no element named "{1}"')
                        raise ValueError(msg.format(component_name, item_name))
                    setattr(component, item_name, value)

        if template:
            # Complain if there are any unhandled entries in the template
            msg = "Template contains unrecognised header components: {0}"
            names = template.keys()
            names = ['"{0}"'.format(name) for name in names]
            names = ", ".join(names)
            raise ValueError(msg.format(names))

    def _calc_lookup_and_data_positions(self, lookup_start):
        """Sets the lookup and data positional information in the header"""
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
        """
        Write all components to the file, _except_ the fixed length header.

        Also updates all the component location and dimension records in the
        fixed-length header.
        That is done here to ensure that these header words are in accord with
        the actual file locations.

        """
        # Go through each component defined for this file type
        for name, component_class in self.COMPONENTS:
            component = getattr(self, name)

            # Construct component position and shape info (or missing-values).
            file_word_position = output_file.tell() // self.WORD_SIZE + 1
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
                msg = 'Component type {0} has {1} dimensions, can not write.'
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

    def _write_to_file(self, output_file):
        """Write out to an open output file."""
        # A reference to the header
        flh = self.fixed_length_header

        # Skip past the fixed length header for now
        output_file.seek(flh._NUM_WORDS * self.WORD_SIZE)

        # Write out the singular headers (i.e. all headers apart from the
        # lookups, which will be done below).
        # This also updates all the fixed-length-header entries that specify
        # the position and size of the other header components.
        self._write_singular_headers(output_file)

        # Update the fixed length header position entries corresponding to
        # the data and lookup
        single_headers_end = output_file.tell() // self.WORD_SIZE
        self._calc_lookup_and_data_positions(single_headers_end + 1)

        if self.fields:
            # Skip the LOOKUP component and write the DATA component.
            # We need to adjust the LOOKUP headers to match where
            # the DATA payloads end up, so to avoid repeatedly
            # seeking backwards and forwards it makes sense to wait
            # until we've adjusted them all and write them out in
            # one go.
            output_file.seek((flh.data_start - 1) * self.WORD_SIZE)
            sector_size = self._WORDS_PER_SECTOR * self.WORD_SIZE

            # Write out all the field data payloads.
            for field in self.fields:
                if field.lbrel != -99.0:

                    # Output 'recognised' lookup types (not blank entries).
                    field.lbegin = output_file.tell() // self.WORD_SIZE

                    # WGDOS packed fields can be tagged with an accuracy of
                    # -99.0; this indicates that they should not be packed,
                    # so reset the packing code here accordingly
                    if field.lbpack % 10 == 1 and int(field.bacc) == -99:
                        field.lbpack = 10*(field.lbpack//10)

                    if field._can_copy_deferred_data(
                            field.lbpack, field.bacc, self.WORD_SIZE):
                        # The original, unread file data is encoded as wanted,
                        # so extract the raw bytes and write them back out
                        # again unchanged; however first trim off any existing
                        # padding to allow the code below to re-pad the output
                        data_bytes = field._get_raw_payload_bytes()
                        data_bytes = data_bytes[
                            :field.lblrec *
                            field._data_provider.DISK_RECORD_SIZE]
                        output_file.write(data_bytes)

                        # Calculate lblrec and lbnrec based on what will be
                        # written (just in case they are wrong or have come
                        # from a pp file)
                        field.lblrec = (
                            field._data_provider.DISK_RECORD_SIZE *
                            field.lblrec // self.WORD_SIZE)
                        field.lbnrec = (
                            field.lblrec -
                            (field.lblrec % -self._WORDS_PER_SECTOR))
                    else:

                        # Strip just the n1-n3 digits from the lbpack value
                        # since the later digits are not relevant
                        lbpack321 = "{0:03d}".format(
                            field.lbpack - ((field.lbpack//1000) % 10)*1000)

                        # Select an appropriate operator for writing the data
                        # (if one is available for the given packing code)
                        if lbpack321 in self.WRITE_OPERATORS:
                            write_operator = self._write_operators[lbpack321]
                        else:
                            msg = ('Cannot save data with lbpack={0} : '
                                   'packing not supported.')
                            raise ValueError(msg.format(field.lbpack))

                        # Use the write operator to prepare the field data for
                        # writing to disk
                        data_bytes, data_size = write_operator.to_bytes(field)

                        # The bytes returned by the operator are in the exact
                        # format to be written
                        output_file.write(data_bytes)

                        # and the operator also returns the exact number of
                        # words/records taken up by the data; this is exactly
                        # what needs to go in the Field's lblrec
                        field.lblrec = data_size

                        # The other record header, lbnrec, is the number of
                        # words/records used to store the data; this may be
                        # different to the above in the case of packed data;
                        # if the packing method has a different word size.
                        # Calculate the actual on-disk word size here
                        size_on_disk = ((write_operator.WORD_SIZE*data_size) //
                                        self.WORD_SIZE)

                        # Padding will also be applied to ensure that the next
                        # block of data is aligned with a sector boundary
                        field.lbnrec = (
                            size_on_disk -
                            (size_on_disk % -self._WORDS_PER_SECTOR))

                    # Pad out the data section to a whole number of sectors.
                    overrun = output_file.tell() % sector_size
                    if overrun != 0:
                        padding = np.zeros(sector_size - overrun, 'i1')
                        output_file.write(padding)

            # Update the fixed length header to reflect the extent
            # of the DATA component.
            flh.data_dim1 = ((output_file.tell() // self.WORD_SIZE) -
                             flh.data_start + 1)

            # Go back and write the LOOKUP component.
            output_file.seek((flh.lookup_start - 1) * self.WORD_SIZE)

            # Write out all the field lookups.
            for field in self.fields:
                field.to_file(output_file)

        # Write the fixed length header - now that we know how big
        # the DATA component was.
        output_file.seek(0)
        self.fixed_length_header.to_file(output_file)


# Import the derived UM File formats
from mule.ff import FieldsFile  # noqa: E402
from mule.lbc import LBCFile  # noqa: E402
from mule.ancil import AncilFile  # noqa: E402
from mule.dump import DumpFile  # noqa: E402
from mule.dumpfromgrib import DumpFromGribFile  # noqa: E402

# Mapping from known dataset types to the appropriate class to use with
# load_umfile
DATASET_TYPE_MAPPING = {
    1: DumpFile,
    2: DumpFile,
    3: FieldsFile,
    4: AncilFile,
    5: LBCFile,
}


def load_umfile(unknown_umfile, stashmaster=None):
    """
    Load a UM file of undetermined type, by checking its dataset type and
    attempting to load it as the correct class.

    Args:
        * unknown_umfile:
            A file or file-like object containing an unknown file
            to be loaded based on its dataset_type.

    Kwargs:
        * stashmaster:
            A :class:`mule.stashmaster.STASHMaster` object containing
            the details of the STASHmaster to associate with the fields
            in the file (if not provided will attempt to load a central
            STASHmaster based on the version in the fixed length header).

    """
    def _load_umfile(file_path, open_file):
        # Read the fixed length header and use the dataset_type to obtain
        # a suitable subclass
        flh = FixedLengthHeader.from_file(open_file)
        file_class = DATASET_TYPE_MAPPING.get(flh.dataset_type)

        # modify the file class if this is a dump on an Arakawa A grid.
        if (flh.dataset_type == 1) and (flh.grid_staggering == 1):
            file_class = DumpFromGribFile

        if not file_class:
            msg = ("Unknown dataset_type {0}, supported types are {1}"
                   .format(flh.dataset_type, str(DATASET_TYPE_MAPPING.keys())))
            raise ValueError(msg)
        umf_new = file_class.from_file(file_path, stashmaster=stashmaster)
        return umf_new

    # Handle the case of the file being either the path to a file to be opened
    # (and closed again) or an existing open file object.
    if isinstance(unknown_umfile, six.string_types):
        file_path = unknown_umfile
        with open(file_path, "rb") as open_file:
            result = _load_umfile(file_path, open_file)
    else:
        open_file = unknown_umfile
        file_path = open_file.name
        result = _load_umfile(file_path, open_file)

    return result
