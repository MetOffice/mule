# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of the UM utilities module, which use the Mule API.
#
# Mule and these utilities are free software: you can redistribute it and/or
# modify them under the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# These utilities are distributed in the hope that they will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with these utilities.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""
CUMF (Compare UM FieldsFiles) is a utility to assist in examining UM files.

Usage:

 * Compare :class:`mule.UMFile` objects with the
   :class:`UMFileComparison` class:

    >>> comp = UMFileComparison(umfile_object1, umfile_object2)

 * This object can be manually examined for details, or you can print either
   a short summary or a full report (note a full report is a super-set of a
   summary report):

   >>> summary_report(comp)
   >>> full_report(comp)

    .. Note::
       The field difference objects behave like the original fields, but their
       data stores the absolute differences.  You could retrieve the data
       using "get_data" to examine it, or write it out to a file.

Global comparison settings:

    The module contains a global "COMPARISON_SETTINGS" dictionary, which
    defines default values for the various options; these may be overidden
    for an entire script/session if desired, or in a startup file e.g.

    >>> from um_utils import cumf
    >>> cumf.COMPARISON_SETTINGS["ignore_missing"] = True

    Alternatively each of these settings may be supplied to the main comparison
    class as keyword arguments.  The available settings are:

    * ignore_templates:
        A dictionary indicating which indices should be ignored when making
        comparisons.  The keys give the names of the components and the values
        are lists of the indices to ignore
        (e.g. {"fixed_length_header": [1,2,3], "lookup": [5,42]})
        (default: ignore creation time in fixed length header only)

    * ignore_missing:
        Flag which sets all positional header indices to be ignored - this is
        useful if the file objects being compared have fields which are
        missing from either file. (default: False)

    * only_report_failures:
        Flag which indicates that the printed output should not contain any
        sections which are simply stating that they agree.  (This cuts down
        on the amount of output for larger files). (default:True)

    * lookup_print_func:
        A callback function which is called for each printed field comparison
        to provide extra information about the fields.  It will be passed 2
        arguments - the comparison field and the stdout object to write to.

    * show_missing:
        Flag which causes a list of fields missing from each file to be
        generated in the report. (default: False)

    * show_missing_max:
        Maximum number of missing fields to display. Set to -1 to indicate no
        maximum. (default: -1)

"""
import re
import sys
import mule
import mule.pp
import errno
import argparse
import textwrap
import numpy as np
from six import StringIO
from collections import defaultdict
from um_utils.stashmaster import STASHmaster
from um_utils.pumf import pprint, _banner
from um_utils.version import report_modules


# The following functions are defaults which are used to print some additional
# information about the lookups being compared (to assist in distinguishing
# between similar fields)
def _print_lookup(field, stdout):
    """Prints the validity time, level and processing information."""
    validity_format = "t1({0:04d}/{1:02d}/{2:02d} {3:02d}:{4:02d}:{5:02d})"
    validity = validity_format.format(*field.raw[1:7])

    lev_format = "lblev({0})/blev({1})"
    lev = lev_format.format(field.raw[33], field.raw[52])

    proc_format = "lbproc({0})"
    proc = proc_format.format(field.raw[25])

    stdout.write("  " + "  ".join([validity, lev, proc])+"\n")


# This version is switched to by default for the "full" output mode
def _print_lookup_full(field, stdout):
    """Prints the entire lookup contents using pumf."""
    pprint(field, stdout=stdout, headers_only=True)


# This dictionary stores a list of global settings that control the
# comparison - when called as a main program these can be overidden by
# the command line arguments, or the user can easily adjust these in
# various ways to customise their output.
COMPARISON_SETTINGS = {
    "ignore_templates": {
        "fixed_length_header": [35, 36, 37, 38, 39, 40, 41],
        },
    "ignore_missing": False,
    "only_report_failures": True,
    "lookup_print_func": _print_lookup,
    "show_missing": False,
    "show_missing_max": -1,
    }

# Lookup indices which should be ignored when the user indicates
# they wish to ignore missing fields from either file
_INDEX_IGNORE_MISSING_FIELDS = [
    29,  # lbegin (field start positions will be offset differently)
    40,  # lbuser(2) (for same reasons as above)
    ]
# Entries from the fixed-length-header which should be ignored when
# the user indicates they wish to ignore missing fields
_INDEX_IGNORE_MISSING_FLH = [
    152,  # Number of lookups (different if some fields are missing)
    153,  # Num prog. fields (different if some are missing)
    160,  # Data start (different if number of lookups is different)
    161,  # Data dim1 (different if some fields are missing)
    162,  # Data dim2 (as above)
    ]

# Lookup indices which must be ignored to allow the index to be
# created that matches lookups in the file against each other
_INDEX_IGNORED_LOOKUP = [
    15,  # lblrec (length on disk could be different due to packing)
    20,  # lbext (extra data may be different)
    22,  # lbrel (may have different header release numbers)
    28,  # lbexp (could be from different experiments)
    29,  # lbegin (field start position won't agree if ordered differently)
    30,  # lbnrec (length on disk could be different due to packing)
    38,  # lbsrce (could be different if model version doesn't agree)
    40   # lbuser(2) (for same reason as lbegin)
    ]


class DifferenceField(mule.Field):
    """
    Difference object - for two :class:`mule.Field` objects.

    A special subclass of :class:`mule.Field` which looks and behaves just
    like the original class, but defines some extra properties that are useful
    when performing a comparison.

    """
    match = None
    """Global matching flag; True if both the lookup and data match."""

    data_match = None
    """Data matching flag; True if the field data matches."""

    data_shape_match = None
    """Data shape matching flag: True if fields are the same shape."""

    compared = None
    """
    Tuple containing the number of points which are different and the total
    number of points in the field.
    """

    rms_diff = None
    """Root-Mean-Squared difference between the two fields."""

    rms_norm_diff_1 = None
    """
    Root-Mean-Squared difference between the two fields, normalised by the
    values in the first field.

    """

    rms_norm_diff_2 = None
    """
    Root-Mean-Squared difference between the two fields, normalised by the
    values in the second field.

    """

    max_diff = None
    """Maximum difference between the two fields."""

    file_1_index = None
    """The field-index of the first field in its original file."""

    file_2_index = None
    """The field-index of the second field in its original file."""

    lookup_comparison = None
    """
    Holds a :class:`ComponentComparison` object that describes any differences
    in the lookup component of the fields.

    """


class DifferenceField2(mule.Field2, DifferenceField):
    """A :class:`DifferenceField` object for :class:`mule.Field2` objects."""
    pass


class DifferenceField3(mule.Field3, DifferenceField):
    """A :class:`DifferenceField` object for :class:`mule.Field3` objects."""
    pass


# Maps header release version number onto a difference field class
_DIFFERENCE_FIELDS = {2: DifferenceField2,
                      3: DifferenceField3,
                      -99: DifferenceField,
                      mule._INTEGER_MDI: DifferenceField3}


class DifferenceOperator(mule.DataOperator):
    """
    This is a simple operator that calculates the difference between
    the data in two fields.

    """
    def __init__(self):
        """Initialise the object."""
        pass

    def new_field(self, fields):
        """
        Create a new field instance from the 2 fields being compared.

        This returns a new :class:`DifferenceField` object with the same
        lookup headers as the first field in the list.  It's data will
        contain the absolute difference of the fields (field_1 - field_2).

        Several statistical quantities will also be calculated and saved
        to the new object, for later inspection.

        Args:
            * fields:
                List containing the 2 :class:`mule.Field` objects
                to be compared.

        .. Note::
            Unlike most other operators the data is retrieved in
            this method as well as in the transform method; because
            we need to know if the fields compare.

        """
        # Copy the header from the first field (if they are being
        # compared the headers should already be the same)
        diff_field_class = _DIFFERENCE_FIELDS.get(fields[0].lbrel,
                                                  DifferenceField)
        new_field = diff_field_class(fields[0]._lookup_ints,
                                     fields[0]._lookup_reals,
                                     None)

        # Copy the STASH entry (if it exists)
        new_field.stash = fields[0].stash

        # Get the data from the fields and check if it matches
        # Note: this is an abnormal use of the operator; usually
        # get_data should not be called in this method, however in
        # this case we need to know if the objects are different
        # immediately
        data1 = fields[0].get_data()
        data2 = fields[1].get_data()

        # A quick helper function which calculates the RMS of the arrays
        def rms(array, mdi_val=None):
            if mdi_val is not None:
                rms_points = array[array != mdi_val]
                if rms_points.size == 0:
                    rms_points = array
            else:
                rms_points = array
            return np.sqrt(np.mean(np.square(rms_points)))

        # Store whether the field matches, and several statistical measures
        # of the differences if any are found
        bool_field = data1 == data2
        new_field.data_match = np.all(bool_field)

        # If the fields aren't the same shape, it isn't possible to calculate
        # anymore comparison information
        new_field.data_shape_match = data1.shape == data2.shape
        if not new_field.data_shape_match:
            new_field.data_match = False
            return new_field

        if not new_field.data_match:
            diff = np.abs(data1 - data2)
            # Maximum absolute difference and RMS difference
            new_field.max_diff = np.max(diff)
            new_field.rms_diff = rms(diff)

            # Get the RMS of each field
            rms_field1 = rms(data1, mdi_val=fields[0].bmdi)
            rms_field2 = rms(data2, mdi_val=fields[1].bmdi)

            # Save the normalised RMS difference as a % of each field (if
            # the field was non-zero)
            if rms_field1 > 0.0:
                new_field.rms_norm_diff_1 = (
                    100.0*(new_field.rms_diff / rms_field1))
            if rms_field2 > 0.0:
                new_field.rms_norm_diff_2 = (
                    100.0*(new_field.rms_diff / rms_field2))

            # Save the number of points compared and the total number of points
            new_field.compared = (bool_field.size - np.sum(bool_field),
                                  bool_field.size)
        else:
            # If nothing was compared ensure everything is set appropriately
            new_field.max_diff = 0.0
            new_field.rms_diff = 0.0
            new_field.rms_norm_diff_1 = 0.0
            new_field.rms_norm_diff_2 = 0.0
            new_field.compared = (0, bool_field.size)

        # Add 1 to lbproc - to indicate it is a different between fields
        # (note the default "Field" objects do not know this property)
        if new_field.lbrel in (2, 3):
            new_field.lbproc += 1

        # Turn off WGDOS packing if used - we can't guarantee that the
        # differences will be able to be packed to the original accuracy
        if new_field.lbpack == 1:
            new_field.lbpack = 0
            new_field.bacc = -99.0

        return new_field

    def transform(self, fields, new_field):
        """Return the absolute differences between the two fields."""
        data1 = fields[0].get_data()
        data2 = fields[1].get_data()
        return data1 - data2


class ComponentComparison(object):
    """
    This class stores an individual comparison result; valid for any
    pair of UM header components.

    """
    match = None
    """Global matching flag; True if both the lookup and data match."""

    compared = None
    """
    Tuple pair indicating how many values were compared and the total
    number of possible comparisons.

    """

    in_file_1 = None
    """Presence flag; True if the first component exists."""

    in_file_2 = None
    """Presence flag; True if the second component exists."""

    same_shape = None
    """Shape flag; True if the components are the same shape."""

    ignored = None
    """Stores a list of any indices which were ignored."""

    diffs = None
    """
    If the components differ, this list stores the differences; it will
    contain one tuple for each difference, consisting of:

        * The index into the components where the difference occurs.
        * The value of the item in component_1.
        * The value of the item in component_2.

    .. Note:
        The length of this list should not be relied on to detect if
        the components match.  If the other flags dictate that the two
        components are not the same shape or either of them are missing,
        the comparison will never be done and diffs will still return
        an empty list.

    """
    component_1 = None
    """A reference to the first component."""

    component_2 = None
    """A reference to the second component"""

    def __init__(self, component_1, component_2, ignore_indices=[]):
        """
        Return elements of the components which do not agree.

        Args:
            * component_1:
                The first component to compare.
            * component_2:
                The second component to compare.

        Kwargs:
            * ignore_indices:
                If provided, a list of indices to ignore when performing
                the check.

        """

        # Initialise the matching and difference list.
        self.match = True
        self.diffs = []
        self.compared = (0, 0)
        self.component_1 = component_1
        self.component_2 = component_2

        # Save a copy of which (if any) indices were ignored (for reporting)
        self.ignored = ignore_indices

        # Check if the components are both present.
        self.in_file_1 = component_1 is not None
        self.in_file_2 = component_2 is not None
        if not (self.in_file_1 and self.in_file_2):
            self.match = self.in_file_1 == self.in_file_2
            return

        # Get the component shapes.
        shape_1 = component_1.raw.shape
        shape_2 = component_2.raw.shape

        # Check if the two are the same shape; save this information then
        # abort the comparison if they aren't compatible
        self.same_shape = shape_1 == shape_2
        if not self.same_shape:
            self.match = False
            return

        # Zip the raw values together - call ravel on them first so that
        # any 2-d component becomes a 1-d equivalent (it won't hurt any
        # actual 1-d arrays).
        component_zip = zip(component_1.raw.ravel(),
                            component_2.raw.ravel())

        # Go through the values; if the elements aren't equal add
        # the index and both element values to the list.
        comparison_count = 0
        for i_element, elements in enumerate(component_zip):
            # Note: call unravel here to work out the original
            # index in the 2-d case.
            index = np.unravel_index(i_element, shape_1)
            if len(index) == 1:
                index = index[0]

            # Only perform the check if this index wasn't
            # explicitly filtered out by the user
            if index not in ignore_indices:
                comparison_count += 1
                if elements[0] != elements[1]:
                        # The list then contains the index and the elements
                        # that are different
                        self.diffs.append((index, elements))

        # Save the number of comparisons performed and the total size (note
        # the "null" quantities padding the components have to be subtracted
        # to give a true value)
        if len(shape_1) == 2:
            null_values = shape_1[0]
        else:
            null_values = 1

        self.compared = (comparison_count - null_values,
                         len(component_1.raw.ravel()) - null_values)

        # Toggle the match flag if any differences were found
        if len(self.diffs) != 0:
            self.match = False


class UMFileComparison(object):
    """
    A structure which stores comparison information between two
    :class:`mule.UMFile` subclasses.

    """

    match = None
    """Global matching flag; True if everything about the files matches."""

    file_1 = None
    """A reference to the first file object."""

    file_2 = None
    """A reference to the second file object."""

    files_are_same_type = None
    """Type flag; True if both files are the same file type."""

    comparisons = None
    """
    A dictionary containing a :class:`ComponentComparison` object for
    each of the possible UM file header components (except the lookup).
    The dictionary keys are the component names (e.g. "fixed_length_header")

    """

    field_comparisons = None
    """
    A list of :class:`DifferenceField` objects; one for each pair of fields
    compared between the two files.

    """
    lookup_ignores = None
    """
    A list of the lookup indices which were ignored for this comparison

    """

    show_missing = False
    """
    Flag which details if a list of missing fields for each file should be
    generated in reports.

    """

    show_missing_max = -1
    """
    The maximum number of missing fields to list. Set to -1 to indicate no
    maximum.

    """

    max_rms_diff_1 = None
    """
    A tuple containing the maximum encountered RMS difference relative to
    the data in the first file, and the index of the field containing it.

    """

    max_rms_diff_2 = None
    """
    A tuple containing the maximum encountered RMS difference relative to
    the data in the second file, and the index of the field containing it.

    """

    unmatched_file_1 = []
    """
    A list containing the indices of any fields which exist in file 1 but
    were not successfully matched to a field in file 2.

    """

    unmatched_file_2 = []
    """
    A list containing the indices of any fields which exist in file 2 but
    were not successfully matched to a field in file 1.

    """

    def __init__(self, um_file1, um_file2, **kwargs):
        """
        Create the comparison object.

        Args:
            * um_file1:
                The first :class:`mule.UMFile` subclass.
            * um_file2:
                The second :class:`mule.UMFile` subclass.

        Kwargs:
            Any other keywords are assumed to be settings to override
            the values in the global COMPARISON_SETTINGS dictionary,
            see the docstring of the :mod:`cumf` module for details

        """

        # Deal with the possible keywords - take the global print settings
        # dictionary as a starting point and add any changes supplied in
        # the call to this method
        comp_settings = COMPARISON_SETTINGS.copy()
        for keyword, value in kwargs.items():
            if keyword in comp_settings:
                comp_settings[keyword] = value
            else:
                msg = "Keyword not recognised: {0}"
                raise ValueError(msg.format(keyword))

        # Global flag to indicate if the files match
        self.match = True

        # Store a reference to the two original file objects
        self.file_1 = um_file1
        self.file_2 = um_file2

        # Check if the files are of the same type
        self.files_are_same_type = type(um_file1) is type(um_file2)
        self.match = self.match and self.files_are_same_type

        # Remove the empty lookups (if the files are fieldsfiles)
        if type(um_file1) is mule.FieldsFile:
            um_file1.remove_empty_lookups()
        if type(um_file2) is mule.FieldsFile:
            um_file2.remove_empty_lookups()

        # First we want to create a list of comparisons of the header
        # compoennts in the file
        self.comparisons = {}

        # Create a list of expected component names; take these from the
        # UMFile base class since it is setup to include all possible/known
        # component names used in the different classes
        component_list = (["fixed_length_header"] +
                          [name for name, _ in mule.UMFile.COMPONENTS])

        # Compare each component, accounting for the possibility that one
        # file might contain it and the other might not
        for name in component_list:
            component_1 = getattr(um_file1, name, None)
            component_2 = getattr(um_file2, name, None)

            # If the template for ignores sets up any indices to ignore
            # for this component extract them here - use the list cast to
            # avoid changing the settings dictionary in-place
            component_ignores = list(
                comp_settings["ignore_templates"].get(name, []))

            if (comp_settings["ignore_missing"] and
                    name == "fixed_length_header"):
                component_ignores.extend(_INDEX_IGNORE_MISSING_FLH)

            comparison = ComponentComparison(component_1, component_2,
                                             component_ignores)
            self.comparisons[name] = comparison

            # Update the global matching if any component fails to match
            self.match = self.match and comparison.match

        # For the fields we will need the difference operator defined above,
        # but it needs to be initialised first
        difference_op = DifferenceOperator()

        # Get the (user) list of lookup elements to ignore
        lookup_ignores = (
            comp_settings["ignore_templates"].get("lookup", []))

        # If the user has chosen to ignore missing fields, add the required
        # elements of the lookup to the ignore list
        if comp_settings["ignore_missing"]:
            lookup_ignores.extend(_INDEX_IGNORE_MISSING_FIELDS)

        lookup_ignores = sorted(list(set(lookup_ignores)))

        # Save the list of ignored lookup indices to this object for later
        self.lookup_ignores = lookup_ignores

        # Save the show-missing option
        self.show_missing = comp_settings["show_missing"]
        self.show_missing_max = comp_settings["show_missing_max"]

        # Initialise the elements which hold the field comparison objects
        self.field_comparisons = []
        self.max_rms_diff_1 = [0, 0]
        self.max_rms_diff_2 = [0, 0]

        # If there aren't any fields in the first file, there isn't anything
        # to compare
        if len(um_file1.fields) == 0:
            # And unless this is allowed or expected, it's also a failure
            if (len(um_file2.fields) != 0 and
                    not comp_settings["ignore_missing"]):
                self.match = False
            return

        # Create a mapping which relates the lookups in the two files (in
        # case the ordering of fields has changed)
        index = self._create_index(um_file1, um_file2, lookup_ignores)

        # If the matchings don't account for all fields, the files cannot
        # completely match (unless the user has specified that this is okay)
        n_indices = len(index)
        if ((n_indices != len(um_file1.fields) or
                n_indices != len(um_file2.fields)) and
                not comp_settings["ignore_missing"]):
            self.match = False

        # Now iterate through the fields whose lookups appear to match
        for ifield_1, ifield_2 in index:

            field_1 = um_file1.fields[ifield_1]
            field_2 = um_file2.fields[ifield_2]

            # Compare the lookups themselves with a comparison object
            lookup_comparison = ComponentComparison(field_1, field_2,
                                                    lookup_ignores)

            # Create a field difference object, which stores information about
            # the differences and the means to obtain a difference map.
            # Note: technically this operator is reading both fields at this
            # point, since it must do this to determine if the fields are
            # different - this is intentional and differs from how operators
            # are commonly used)
            diff_field = difference_op([field_1, field_2])

            diff_field.file_1_index = ifield_1
            diff_field.file_2_index = ifield_2
            diff_field.lookup_comparison = lookup_comparison

            # Keep a running total of the largest RMS differences
            if diff_field.rms_norm_diff_1 is not None:
                if self.max_rms_diff_1[0] < diff_field.rms_norm_diff_1:
                    self.max_rms_diff_1 = (diff_field.rms_norm_diff_1,
                                           ifield_1 + 1)

            if diff_field.rms_norm_diff_2 is not None:
                if self.max_rms_diff_2[0] < diff_field.rms_norm_diff_2:
                    self.max_rms_diff_2 = (diff_field.rms_norm_diff_2,
                                           ifield_2 + 1)

            # The field object only matches if both the lookups and the
            # data match
            diff_field.match = (lookup_comparison.match and
                                diff_field.data_match)

            # Update the global matching if any field or lookup fails to match
            self.match = self.match and diff_field.match

            # Append the information and objects to the comparison list
            self.field_comparisons.append(diff_field)

    def _create_index(self, um_file1, um_file2, lookup_ignores=[]):
        """
        Method to attempt to match fields in the two files by their lookups.

        """
        # Create a base set of lookups to ignore when trying to match fields,
        # these entries can change very readily even in files which do
        # technically compare, so should always be ignored
        set_ignored_lookups = set(_INDEX_IGNORED_LOOKUP)

        # The user may additionally have provided their own set of indices
        # to ignore - combine them with the default ones here to make a
        # complete set
        set_ignored_lookups = set_ignored_lookups | set(lookup_ignores)

        # Generate a set of indices the length of the first lookup header
        # in the file and take its compliment with the list above to end up
        # with only the indices we wish to compare as a list
        set_lookups_to_check = set(range(1, len(um_file1.fields[0].raw)))
        set_lookups_to_check = set_lookups_to_check - set_ignored_lookups
        lookups_to_check = sorted(list(set_lookups_to_check))

        # Create a list of the indices of the fields in file 1, the indices
        # will be removed from this list as the fields are processed
        set_unmatched_in_file1 = set(range(len(um_file1.fields)))
        index = []

        # Create a dictionary storing sets of the indices in file 2 separated
        # according to their stash code, with that stash code as the keys
        file_2_fields_by_stash = defaultdict(list)
        for ifield2, field in enumerate(um_file2.fields):
            file_2_fields_by_stash[field.lbuser4].append(ifield2)

        # Can now go through the fields in file 1 and identify matches
        for ifield1, field1 in enumerate(um_file1.fields):
            lookup1 = field1.raw[lookups_to_check]
            # Look for matching lookup in file_2.fields
            stash_item = field1.lbuser4
            if stash_item in file_2_fields_by_stash:
                for ifield2 in file_2_fields_by_stash[stash_item]:
                    # When comparing each lookup, check only the indices that
                    # were specified above (some indices will rarely match)
                    lookup2 = um_file2.fields[ifield2].raw[lookups_to_check]
                    if all(lookup1 == lookup2):
                        # Save the indices of the matched fields, and remove
                        # them from both sets so that they can't be matched
                        # multiple times and for some minor performance savings
                        index.append((ifield1, ifield2))
                        set_unmatched_in_file1.remove(ifield1)
                        file_2_fields_by_stash[stash_item].remove(ifield2)
                        break  # Move to next field in file 1

        # Any indices left in either list represent fields for which a
        # match was not found between the files.  Save these indices
        # so that they can be referred to in any reporting
        self.unmatched_file_1 = sorted(
            list(set_unmatched_in_file1))

        # The file 2 dictionary needs to be unravelled from the stash code
        # dictionary and back into a flat list
        self.unmatched_file_2 = []
        for stash_item in file_2_fields_by_stash:
            self.unmatched_file_2.extend(file_2_fields_by_stash[stash_item])
        self.unmatched_file_2 = sorted(self.unmatched_file_2)

        return index


def summary_report(comparison, stdout=None):
    """
    Print a report giving a brief summary of a comparison object.

    Args:
        * comparison:
            A :class:`UMFileComparison` object, populated with the
            differences between two files.

    Kwargs:
        * stdout:
            A open file-like object to write the report to.

    """
    # Setup output
    if stdout is None:
        stdout = sys.stdout

    stdout.write(_banner("CUMF-II Comparison Report")+"\n")

    # Report the names of the files
    stdout.write("File 1: {0}\n".format(comparison.file_1._source_path))
    stdout.write("File 2: {0}\n".format(comparison.file_2._source_path))

    # First of all do the files compare overall
    if comparison.match:
        stdout.write("Files compare\n")
    else:
        stdout.write("Files DO NOT compare\n")

    # Warn if the files are not the same type
    if not comparison.files_are_same_type:
        stdout.write("WARNING: Files are not the same type!  This is likely "
                     "to cause unknown differences\n")

    # Create the component list from the base file class
    component_list = (["fixed_length_header"] +
                      [name for name, _ in mule.UMFile.COMPONENTS])

    # First pass loop to present a quick overview of what exactly is wrong
    for name in component_list:
        comp_comp = comparison.comparisons[name]
        if not comp_comp.match:
            stdout.write(
                "  * {0} differences in {1} (with {2} ignored indices)\n"
                .format(len(comp_comp.diffs), name, len(comp_comp.ignored)))
        elif len(comp_comp.ignored) > 0:
            stdout.write(
                "  * 0 differences in {0} (with {1} ignored indices)\n"
                .format(name, len(comp_comp.ignored)))

    if len(comparison.field_comparisons) > 0:
        field_matches = np.array(
            [(comp_field.match, comp_field.data_match)
                for comp_field in comparison.field_comparisons])
        n_diff, n_data_diff = np.sum(np.bitwise_not(field_matches), axis=0)
        stdout.write("  * {0} field differences, of which {1} are in data\n"
                     .format(n_diff, n_data_diff))
    stdout.write("\n")

    # Summarise the field differences
    fields_compared = len(comparison.field_comparisons)
    if comparison.unmatched_file_1 is None:
        total_fields = 0
    else:
        total_fields = (fields_compared +
                        len(comparison.unmatched_file_1) +
                        len(comparison.unmatched_file_2))
    matches = sum([fcomp.match for fcomp in comparison.field_comparisons])
    stdout.write("Compared {0}/{1} fields, with {2} matches\n"
                 .format(fields_compared, total_fields, matches))

    # If not all the fields were matched, report on the distribution of the
    # mis-match
    if len(comparison.unmatched_file_1) > 0:
        msg = "{0} fields found in file 1 were not in file 2\n"
        stdout.write(msg.format(len(comparison.unmatched_file_1)))
    if len(comparison.unmatched_file_2) > 0:
        msg = "{0} fields found in file 2 were not in file 1\n"
        stdout.write(msg.format(len(comparison.unmatched_file_2)))

    # If not all fields were compared, report here, and exit if none were
    # compared, unless --show-missing was requested. In that case continue
    # far enough to print lookup ignores, which are now relevant.
    if fields_compared != total_fields and fields_compared == 0:
        if not comparison.show_missing:
            stdout.write("\n")
            return

    # Report missing fields if requested
    if comparison.show_missing:
        if fields_compared == 0:
            stdout.write("Not listing specific missing fields,"
                         " because all fields are missing from both files."
                         " (No fields are common.)\n")
        else:
            msg = " * {0}/{1}: {2} -{3}\n"
            counts = [comparison.unmatched_file_1, comparison.unmatched_file_2]
            umfiles = [comparison.file_1, comparison.file_2]
            for ifile, (count, umfile) in enumerate(zip(counts, umfiles)):
                total_missing_shown = 0
                file_a = str(ifile % 2 + 1)
                file_b = str((ifile + 1) % 2 + 1)
                if len(count) > 0:
                    stdout.write("\n")
                    stdout.write("Fields in file {0} but not file {1}:\n"
                                 .format(file_a, file_b))
                    for index in count:
                        if (total_missing_shown >=
                                comparison.show_missing_max and
                                comparison.show_missing_max != -1):
                            stdout.write(
                                "  More fields are missing from file {0:s},"
                                .format(file_b) +
                                " but the print maximum has been reached.\n")
                            break
                        if umfile.fields[index].stash is not None:
                            if umfile.fields[index].stash.name is not None:
                                stashname = umfile.fields[index].stash.name
                            else:
                                stashname = "Unknown STASH (code: {})".format(
                                    umfile.fields[index].lbuser4)
                        else:
                            stashname = "Unknown STASH (code: {})".format(
                                umfile.fields[index].lbuser4)
                        lookup_info = StringIO()
                        _print_lookup(umfile.fields[index], lookup_info)
                        stdout.write(msg.format(index+1,
                                                len(umfile.fields),
                                                stashname,
                                                lookup_info.getvalue()))
                        lookup_info.close()
                        total_missing_shown = total_missing_shown + 1

    # Report which indices were ignored from the lookups
    if len(comparison.lookup_ignores) > 0:
        ignored = []
        stdout.write("\n")
        for index in comparison.lookup_ignores:
            indexstr = str(index)
            for map_name, map_ind in mule._LOOKUP_HEADER_3:
                if map_ind == index:
                    indexstr = "{0} ({1})".format(index, map_name)
                    break
            ignored.append(indexstr)
        stdout.write("Ignored lookup indices:\n  Index {0}\n"
                     .format("\n  Index ".join(ignored)))

    stdout.write("\n")

    # If not all fields were compared, report here, and exit if none were
    # compared
    if fields_compared != total_fields and fields_compared == 0:
        return

    # Report on the maximum RMS diff percentage
    if comparison.max_rms_diff_1[0] > 0.0:
        stdout.write(
            "Maximum RMS diff as % of data in file 1: {0!r} (field {1})\n"
            .format(*comparison.max_rms_diff_1))
    if comparison.max_rms_diff_2[0] > 0.0:
        stdout.write(
            "Maximum RMS diff as % of data in file 2: {0!r} (field {1})\n"
            .format(*comparison.max_rms_diff_2))

    if (comparison.max_rms_diff_1[0] > 0.0 or
            comparison.max_rms_diff_2[0] > 0.0):
        stdout.write("\n")


def full_report(comparison, stdout=None, **kwargs):
    """
    Print a report giving a full analysis of a comparison object.

    Args:
        * comparison:
            A :class:`UMFileComparison` object, populated with the
            differences between two files.

    Kwargs:
        * stdout:
            A open file-like object to write the report to.

    Other Kwargs:
        Any other keywords are assumed to be settings to override
        the values in the global COMPARISON_SETTINGS dictionary,
        see the docstring of the :mod:`cumf` module for details

    """
    # Setup output
    if stdout is None:
        stdout = sys.stdout

    # Deal with the possible keywords - take the global print settings
    # dictionary as a starting point and add any changes supplied in
    # the call to this method
    comp_settings = COMPARISON_SETTINGS.copy()
    for keyword, value in kwargs.items():
        if keyword in comp_settings:
            comp_settings[keyword] = value
        else:
            msg = "Keyword not recognised: {0}"
            raise ValueError(msg.format(keyword))

    # The full report contains the summary at the beginning
    summary_report(comparison, stdout)

    # Create the component list from the base file class
    component_list = (["fixed_length_header"] +
                      [name for name, _ in mule.UMFile.COMPONENTS])

    # Get the verbosity setting from the dictionary
    only_report_failures = comp_settings["only_report_failures"]

    # Define a quick function for convenience since it's used in a two
    # places below - this is used to format the index report nicely
    def report_index_errors(diffmap, stdout, name_mapping):
        to_output = []
        max_width = [0, 0, 0]
        # Capture the widest width needed for each element
        for index, (value_1, value_2) in diffmap:
            # Set the index string to be the numerical value
            indexstr = str(index)
            if name_mapping is not None:
                # If a mapping was given, add the associated name here
                for map_name, map_ind in name_mapping:
                    if map_ind == index:
                        indexstr = "{0} ({1})".format(index, map_name)
                        break

            valstr_1 = str(value_1)
            valstr_2 = str(value_2)
            max_width[0] = max(max_width[0], len(indexstr))
            max_width[1] = max(max_width[1], len(valstr_1))
            max_width[2] = max(max_width[2], len(valstr_2))
            to_output.append((indexstr, valstr_1, valstr_2))

        # Construct an appropriate width statement
        width_format = ("  Index {0:"+str(max_width[0])+"} differs - "
                        "file_1: {1: >"+str(max_width[1])+"}  "
                        "file_2: {2: >"+str(max_width[2])+"}\n")

        # Output the nicely formatter lines
        for output in to_output:
            stdout.write(width_format.format(*output))

    # Now report on differences bettween the components
    for name in component_list:
        comp_comp = comparison.comparisons[name]

        # Prepare a message showing the number of values compared
        msg_values = "(compared {0}/{1} values)".format(*comp_comp.compared)

        # Also report the indices that were ignored
        if len(comp_comp.ignored) > 0:
            ignored = []
            mapping = comp_comp.component_1.HEADER_MAPPING
            for index in comp_comp.ignored:
                indexstr = str(index)
                if mapping is not None:
                    for map_name, map_ind in mapping:
                        if map_ind == index:
                            indexstr = "{0} ({1})".format(index, map_name)
                            break
                ignored.append(indexstr)
            msg_ignore = ("\nIgnored indices:\n  Index {0}"
                          .format("\n  Index ".join(ignored)))
            msg_values += msg_ignore

        if comp_comp.match:
            # If they agree simply state this and move on
            if not only_report_failures:
                stdout.write(_banner(name))
                stdout.write("Components compare {0}\n\n".format(msg_values))
        else:
            # If they disagree move onto the reason/s why
            stdout.write(_banner(name))
            stdout.write("Components DO NOT compare {0}\n".format(msg_values))

            # Check to see if they component was missing in either file
            if not comp_comp.in_file_1:
                stdout.write("Component missing from file 1\n")
            if not comp_comp.in_file_2:
                stdout.write("Component missing from file 2\n")
            # ... and if they were the same shape
            if not comp_comp.same_shape:
                stdout.write("Component shape do not match\n")

            # Get the possible names for the indices (1d headers only)
            if len(comp_comp.component_1.shape) == 1:
                index_name_ref = comp_comp.component_1.HEADER_MAPPING
            else:
                index_name_ref = None

            stdout.write("Component differences:\n")
            report_index_errors(comp_comp.diffs, stdout, index_name_ref)
            stdout.write("\n")

    # Get the total number of fields
    fields_compared = len(comparison.field_comparisons)

    # Get the printing callback function from the settings dictionary
    print_lookups = comp_settings["lookup_print_func"]

    # If this is the default pumf case, and the callback hasn't been
    # overidden by the user, switch it for the more verbose version
    if not only_report_failures and print_lookups is _print_lookup:
        print_lookups = _print_lookup_full

    # Each field is treated individually for both its lookup and data parts
    for ifield, comp_field in enumerate(comparison.field_comparisons):

        comp_lookup = comp_field.lookup_comparison

        # First a simple message explaining if the field broadly compares
        heading = "Field {0}/{1} ".format(ifield + 1, fields_compared)
        if comp_field.stash is not None:
            heading += "- " + comp_field.stash.name

        if comp_field.match:
            # If the field compares report this and continue
            if only_report_failures:
                continue
            stdout.write(_banner(heading))
            stdout.write("Field compares\n")
        else:
            stdout.write(_banner(heading))
            # Report the status of the two components separately
            if comp_lookup.match:
                stdout.write("Lookup compares, ")
            else:
                stdout.write("Lookup DOES NOT compare, ")
            if comp_field.data_match:
                stdout.write("data compares\n")
            else:
                stdout.write("data DOES NOT compare\n")

        # Indicate how many lookup values were actually compared
        stdout.write("Compared {0}/{1} lookup values.\n"
                     .format(*comp_lookup.compared))

        # Print some extra information about the fields
        stdout.write("File_1 lookup info:\n")
        print_lookups(comp_field.lookup_comparison.component_1, stdout)

        # Report if there was a difference in the ordering of the fields
        if comp_field.file_1_index != comp_field.file_2_index:
            msg = ("Order difference: field is #{0} in file 1 "
                   "but #{1} in file 2\n")
            stdout.write(msg.format(comp_field.file_1_index+1,
                                    comp_field.file_2_index+1))

        if not comp_lookup.match:
            # If there were any lookup differences report them
            stdout.write("Lookup differences:\n")
            report_index_errors(comp_lookup.diffs, stdout,
                                comp_field.HEADER_MAPPING)

        if not comp_field.data_shape_match:
            # If the data shape wasn't the same there isn't much to report here
            stdout.write("Data shapes are different, no comparison possible\n")
        elif not comp_field.data_match:
            # If there were any data differences report them
            stdout.write("Data differences:\n")
            stdout.write("  Number of point differences  : {0}/{1}\n"
                         .format(*comp_field.compared))
            stdout.write("  Maximum absolute difference  : {0!r}\n"
                         .format(comp_field.max_diff))
            stdout.write("  RMS difference               : {0!r}\n"
                         .format(comp_field.rms_diff))
            if comp_field.rms_norm_diff_1 is None:
                stdout.write("  RMS diff as % of file_1 data : "
                             "NaN (File 1 data all zero) \n")
            else:
                stdout.write("  RMS diff as % of file_1 data : {0!r}\n"
                             .format(comp_field.rms_norm_diff_1))
            if comp_field.rms_norm_diff_2 is None:
                stdout.write("  RMS diff as % of file_2 data : "
                             "NaN (File 2 data all zero) \n")
            else:
                stdout.write("  RMS diff as % of file_2 data : {0!r}\n"
                             .format(comp_field.rms_norm_diff_2))

        stdout.write("\n")


def _main():
    """
    Main function; accepts command line arguments to override the comparison
    settings and provides a pair of UM files to compare.

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] [options] file_1 file_2

    This script will compare all headers and data from two UM files,
    and write a report describing any differences to stdout.  The
    assumptions made by the comparison may be customised with a
    variety of options (see below).
    """
    title = _banner(
        "CUMF-II - Comparison tool for UM Files, version II "
        "(using the Mule API)", banner_char="=")

    # Include a list of the component names as they appear in Mule
    component_names = ", ".join(
        (["fixed_length_header"] +
         [name for name, _ in mule.UMFile.COMPONENTS] +
         ["lookup"]))

    help_epilog = """
    possible component names for the ignore option:
    {0}

    for details of the indices see UMDP F03:
      https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf
    """.format(textwrap.fill(component_names,
                             width=80,
                             initial_indent=4*" ",
                             subsequent_indent=8*" "))

    class ShowMissingAction(argparse.Action):
        def __init__(self, option_strings, dest, nargs=None, **kwargs):
            super(ShowMissingAction, self).__init__(
                option_strings, dest, **kwargs)

        def __call__(self, parser, namespace, values, option_string=None):
            setattr(namespace, "show_missing", [True, values])

    # Setup the parser
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        epilog=textwrap.dedent(help_epilog),
        formatter_class=argparse.RawTextHelpFormatter,
        )

    # No need to output help text for the two input files (these are obvious)
    parser.add_argument("file_1", help=argparse.SUPPRESS)
    parser.add_argument("file_2", help=argparse.SUPPRESS)

    parser.add_argument(
        '--ignore',
        help="ignore specific indices of a component; provide the name of \n"
        "the component and a comma separated list of indices or ranges \n"
        "(i.e. M:N) to ignore.  This may be specified multiple times to \n"
        "ignore indices from more than one component\n ",
        metavar="component_name=index1[,index2][...]",
        action="append")
    parser.add_argument(
        '--ignore-missing',
        action='store_true',
        help="if present, positional headers will be ignored (required if \n"
        "missing fields from either file should not be considered a failure \n"
        "to compare)\n ")
    parser.add_argument(
        '--diff-file',
        help="a filename to write a new UM file to which contains the \n"
        "absolute differences for any fields that differ\n ",
        metavar="filename")
    parser.add_argument(
        '--full', action='store_true',
        help="if not using summary output, will increase the verbosity by \n"
        "reporting on all comparisons (default behaviour is to only report \n"
        "on failures)\n ")
    parser.add_argument(
        '--summary', action='store_true',
        help="print a much shorter report which summarises the differences \n"
        "between the files without going into much detail\n ")
    parser.add_argument(
        "--stashmaster",
        help="either the full path to a valid stashmaster file, or a UM \n"
        "version number e.g. '10.2'; if given a number cumf will look in \n"
        "the path defined by: \n"
        "  mule.stashmaster.STASHMASTER_PATH_PATTERN \n"
        "which by default is : \n"
        "  $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A\n")
    parser.add_argument(
        "--show-missing",
        nargs='1',
        action=ShowMissingAction,
        default=[False, -1],
        metavar='[=N]',
        help="display missing fields from either file. If given, N is the\n"
        " maximum number of fields to display.\n")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    # set the default value for --show-missing if none was given
    try:
        sys.argv[sys.argv.index("--show-missing")] = "--show-missing=-1"
    except ValueError:
        pass

    args = parser.parse_args()

    # Print version information
    print(_banner("(CUMF-II) Module Information")),
    report_modules()
    print("")

    # Process ignoring indices from
    if args.ignore is not None:
        for ignore_list in args.ignore:
            if "=" in ignore_list:
                name, indices = ignore_list.split("=")
                ignores = []
                for arg in indices.split(","):
                    if re.match(r"^\d+$", arg):
                        ignores.append(int(arg))
                    elif re.match(r"^\d+:\d+$", arg):
                        ignores += range(*map(int, arg.split(":")))
                    else:
                        msg = "Unrecognised index in ignore list: {0}"
                        raise ValueError(msg.format(ignore_list))
                COMPARISON_SETTINGS["ignore_templates"][name] = ignores

    # Process the ignore missing flag
    COMPARISON_SETTINGS["ignore_missing"] = args.ignore_missing
    COMPARISON_SETTINGS["show_missing"] = args.show_missing[0]
    if args.show_missing[0]:
        COMPARISON_SETTINGS["show_missing_max"] = args.show_missing[1]

    # If provided, load the given stashmaster
    stashm = None
    if args.stashmaster is not None:
        if re.match(r"\d+.\d+", args.stashmaster):
            stashm = STASHmaster.from_version(args.stashmaster)
        else:
            stashm = STASHmaster.from_file(args.stashmaster)
        if stashm is None:
            msg = "Cannot load user supplied STASHmaster"
            raise ValueError(msg)

    if args.full:
        COMPARISON_SETTINGS["only_report_failures"] = False
        COMPARISON_SETTINGS["show_missing"] = True

    # Check if either of these are pp files
    um_files = []
    pp_mode = False
    for input_file in (args.file_1, args.file_2):
        if mule.pp.file_is_pp_file(input_file):
            # Make an empty fieldsfile object and attach the pp file's
            # field objects to it
            pp_mode = True
            um_file = mule.FieldsFile()
            um_file.fields = mule.pp.fields_from_pp_file(input_file)
            um_file._source_path = input_file
            if stashm is not None:
                um_file.attach_stashmaster_info(stashm)
        else:
            um_file = mule.load_umfile(input_file, stashmaster=stashm)
        um_files.append(um_file)

    comparison = UMFileComparison(um_files[0], um_files[1])

    # Now print a report to stdout, if a SIGPIPE is received handle
    # it appropriately
    try:
        if args.summary:
            summary_report(comparison)
        else:
            full_report(comparison)
    except IOError as error:
        if error.errno != errno.EPIPE:
            raise

    # If requested, and any data differences exist, write to diff file
    if args.diff_file is not None:
        # Cannot do this if a pp file was involved
        if pp_mode:
            msg = ("At least one of the files was a pp file, cannot "
                   "produce a difference file in this case")
            raise ValueError(msg)

        diff_file = args.diff_file
        new_ff = um_files[0].copy()
        new_ff.fields = [field for field in comparison.field_comparisons
                         if not field.data_match and field.data_shape_match]

        # If any of these fields require the land-sea-mask to be written out
        # add it to the start of the file list here
        mask_required = [field.lbpack % 100 != 0 for field in new_ff.fields]
        if any(mask_required):
            lsm = None
            for field in um_files[0].fields:
                if field.lbrel in (2, 3) and field.lbuser4 == 30:
                    lsm = field
                    break
            if lsm is None:
                msg = "Unable to write diff file, land-sea mask not present"
                raise ValueError(msg)
            new_ff.fields.insert(0, lsm)

        if len(new_ff.fields) > 0:
            new_ff.to_file(diff_file)


if __name__ == "__main__":
    _main()
