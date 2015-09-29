#!/usr/bin/env python
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
Mule standard utility which provides a means to print out information
contained in a FieldsFileVariant
"""

import sys
import numpy as np
from mule import load_umfile, FieldsFile, _LOOKUP_HEADERS
from um_utils.stashmaster import STASHmaster

# This file is split into 2 parts - the actual logic making up the iteration
# through the file contents is towards the bottom; this upper part of the file
# merely deals with setting up default printing functions (these are able to
# be overridden by the user)
_PRINT_COLS=4
_STASHMASTER = STASHmaster()

def banner_print(message):
    print "\n{0:s}\n* {1:s} *\n{0:s}".format("%"*(len(message)+4),message)

def _generic_header_print_gen(offset=0, name="Unknown Array", banner=True):
    """
    A factory for returning the basic default method used to print the values
    of a given header array; it accepts a 1 or 2-dimensional np.ndarray as
    argument and it will print each element prefixed by its numerical index.
    In the case of a 2-dimensional array it will print each slice across the
    extra dimension as if it were a separate array.

    A few settings may be "baked" into the returned function:

        offset - will force the index prefixes to be offset by the given amount

        name   - a name associated with the array, to print before it

        banner - if True the name above will be printed as a banner
    
    """
    def print_single(headers):
        """
        This function prints a 1-dimensional np.ndarray, applying the settings
        given to the function above
        """
        # The FieldsFileVariant uses object-arrays for some parts of the header,
        # these are intentionally offset from zero to mimic Fortran-indexing
        # therefore remove the empty zero-th value before continuing
        if headers[0] is None:
            headers = headers[1:]
        n_heads = len(headers)

        # Construct an array of tuples storing the (1-based) index (further
        # offset if required) and the corresponding header value
        idx_head = zip(range(1 + offset,n_heads + 1 + offset), headers)

        # Loop across these indices in chunks controlled by _PRINT_COLS, so
        # that a newline is started after the required number of columns
        for i in range(0, n_heads, _PRINT_COLS):
            print "".join(["{0:8}: {1:12g} ".format(idx, head)
                           for idx, head in idx_head[i:i+_PRINT_COLS]])

    def generic_print(headers_in):
        """
        Default method for printing general headers.
        """
        if hasattr(headers_in, "raw"):
            headers = headers_in.raw
        else:
            headers = headers_in
        
        head_shape = headers.shape
        if len(head_shape) == 1:
            # For 1-dimensional arrays simply print the contents using the
            # function above
            if banner:
                banner_print(name)
            else:
                print(name)
            print_single(headers[1:])
        elif len(head_shape) == 2:
            dim_2 = head_shape[1]
            for element in range(1, dim_2):
                # For 2-dimensional arrays append each slice's title with
                # a fractional indicator of which slice is being output
                if banner:
                    banner_print(
                        name + " ({0:d}/{1:d})".format(element,dim_2 - 1))
                else:
                    print(name + " ({0:d}/{1:d})".format(element,dim_2 - 1))
                        
                print_single(headers[:,element])
        else:
            raise ValueError("Unable to print header, max dimension > 2")
        
    return generic_print


def _setup_default_formatters():
    """
    Sets up the default dictionary of formatters; these are designed to be
    overridable by the user without having to directly edit this code.  The
    defaults setup here are broadly similar to the older UM utilitiy "pumf"
    """
    # The formatter dictionary contains one entry for each type of entity that
    # may be encountered in the file
    formatters = dict()

    # Generate a function for printing the fixed length header
    flh_title = "fixed_length_header"
    formatters[flh_title] = _generic_header_print_gen(
                            name=flh_title.replace("_", " ").capitalize())
    
    # Get the names for the main header entries - take these from the
    # definitions of a FieldsFile
    entries = [name for name, _ in FieldsFile._COMPONENTS]

    # Use the factory method above to create a generic print function for
    # each element in the file, and bind it to the formatter dictionary
    for entry in entries:
        title = entry.replace("_", " ").capitalize()
        formatters[entry] = _generic_header_print_gen(name=title)

    # In the print_lookup function below, we will want to access the named
    # version of each lookup header item. The names must be unpicked from the
    # mule_core file but since they depend on what header release the lookup
    # contains, we pre-calculate them here to be retrieved in the method 
    lookup_version = dict()
    for version in _LOOKUP_HEADERS:
        lookup_version[version] = []
        for name, _ in _LOOKUP_HEADERS[version]:
            lookup_version[version].append(name)

    # We also want to print the lookup values by index, and again since this
    # will ultimately be the same for every lookup, pre-define the functions
    # here so their references can be re-used inside the method below
    print_ints = _generic_header_print_gen(name="Integer (Words  1-45)",
                                           banner=False)
    # Note we apply an offset here to the real headers so that their indices
    # correspond to those in UMDP F03 instead of resetting to 1
    print_real = _generic_header_print_gen(name="Real (Words 46-64)",
                                           offset=45,
                                           banner=False)

    # And similarly, the time formatting is slightly different for the two
    # different header releases, so create a lookup for it here
    d_format = {2:
                "Valid at  {0:02d}:{1:02d}Z {3:02d}/{4:02d}/{5:04d} "
                "(Day {2:03d})\n"
                "Data time {6:02d}:{7:02d}Z {9:02d}/{10:02d}/{11:04d} "
                "(Day {8:03d})",
                # The difference is that release (2) above, uses the day
                # number in place of the seconds
                3:
                "Valid at  {0:02d}:{1:02d}:{2:02d}Z {3:02d}/{4:02d}/{5:04d}\n"
                "Data time {6:02d}:{7:02d}:{8:02d}Z {9:02d}/{10:02d}/{11:04d}"}

    def print_lookup(field, ifield):
        """
        Default method for printing the lookup headers
        """
        # Start by printing a banner which includes the Field number and the
        # raw lookup values
        banner_print("Lookup Headers (Field {0:d})".format(ifield+1))
        print_ints(field._lookup_ints)
        print_real(field._lookup_reals)

        # Check to see if the header can be understood
        release = field.raw[22]
        if release not in lookup_version:
            print ("HEADER RELEASE VERSION {0:d} NOT KNOWN\n"
                   "UNABLE TO PRINT DETAILED FIELD INFO"
                   .format(release))
            return

        # If it can print the name from the STASH entry
        if _STASHMASTER.has_key(field.lbuser4):
            name = "\""+_STASHMASTER[field.lbuser4].name+"\""
        else:
            name = "\"UNKNOWN STASH CODE {0:d}\"".format(field.lbuser4)
        print ("\n" + name)

        # And some time information (the format is set above, to handle the
        # differences between the header releases)
        print (d_format[release].format(field.raw[4],  field.raw[5],
                                        field.raw[6],  field.raw[3],
                                        field.raw[2],  field.raw[1],
                                        field.raw[10], field.raw[11],
                                        field.raw[12], field.raw[9],
                                        field.raw[8],  field.raw[7]))

        # Finally re-print the header values using the header names rather
        # than their indices.  These are taken from mule_core but cached above
        # to save re-producing them here for every field
        names = lookup_version[release]
        headers = [getattr(field, name) for name in names]
        name_head = zip(names, headers)
        n_heads = len(names)
        # This is similar to the default print function for the other header
        # entries, only using names instead of indices
        for i in range(0, n_heads, _PRINT_COLS):
            print "".join(["{0:8}: {1:12g} ".format(name.upper(), head)
                        for name, head in name_head[i:i+_PRINT_COLS]])

    # Bind the above method as the lookup header formatter
    formatters["lookup"] = print_lookup

    # It isn't practical to print all of the data, but we can print a handful
    # of statistics about its values; this dictionary maps the name to use
    # in the printed output to the function which should be called on each
    # data array
    stats = [("maximum", np.max),
             ("minimum", np.min),
             ("mean", np.mean)]


    def print_data_stats(field):
        """
        Default method for printing information about field data
        """
        # Extract the field data (including unpacking etc.)
        data = field.get_data()

        results = []
        for name, func in stats:
            res = func(data)
            if not np.isnan(res):
                res = "{0:12g}".format(float(res))
            results.append((name, res))

        # Again this is the same construct used in a few places above to print
        # the results in nice columns (but using names rather than indices)
        for i in range(0, len(stats), _PRINT_COLS):
            print "".join(["{0:8}: {1:12s} ".format(name.upper(), res)
                        for name, res in results[i:i+_PRINT_COLS]])

    # Bind the above method as the data formatter
    formatters["data"] = print_data_stats

    return formatters

# Setup the default formatters 
FORMATTERS = _setup_default_formatters()

def process(input_file):
    """
    Iterate through the structure of the given FieldsFileVariant and apply the
    methods specified in the stat.FORMATTERS dictionary to each section
    """
    # Load the file
    print "Reading UM File: {0:s}".format(input_file)
    umf = load_umfile(input_file)

    # Process the fixed length header (if a formatter exists for it)
    if FORMATTERS.has_key("fixed_length_header"):
        FORMATTERS["fixed_length_header"](umf.fixed_length_header)

    # Process each of the main file headers (if formattters exist for them)
    for entry, _ in umf._COMPONENTS:
        if FORMATTERS.has_key(entry) and hasattr(umf, entry):
            if getattr(umf,entry) is not None and FORMATTERS[entry] is not None:
                FORMATTERS[entry](getattr(umf,entry))

    # Iterate through the lookup headers, ignoring empty entries and process
    # the lookup itself and the data (if formatters exist for these)
    for ifield, field in enumerate(umf.fields):
        if field.raw[1] == -99:
            break
        if FORMATTERS.has_key("lookup"):
            FORMATTERS["lookup"](field, ifield)
        if FORMATTERS.has_key("data") and field.raw[22] in (2,3):
            FORMATTERS["data"](field)

if __name__ == "__main__":

    process(sys.argv[1])
    


