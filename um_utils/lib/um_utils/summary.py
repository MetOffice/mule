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
SUMMARY is a utility to assist in examining the lookup headers from UM files.

Usage:

 * Summarise a :class:`mule.UMFile` object:

    >>> summary.field_summary(umfile_object)

Global print settings:

    The module contains a global "PRINT_SETTINGS" dictionary, which defines
    default values for the various options; these may be overidden for an
    entire script/session if desired, or in a startup file e.g.

    >>> from um_utils import summary
    >>> summary.PRINT_SETTINGS["column_names"] = ["stash_name", "lbft"]

    Alternatively each of these settings may be supplied to the main
    "field_summary" routine as keyword arguments.  The available settings are:

    * column_names:
        A list giving the names for the columns in the summary, in the order
        they should appear.  Names are the exact names from the
        :class:`mule.Field` header mappings (e.g. "lbuser4", "lbft") or one
        of the following "special" names, which result in the following:

            * "stash_name":
                Gives the name from the stashmaster (if available).
            * "index":
                Gives the index of the field.
            * "t1" or "t2":
                Gives a nicely formatted time/date string corresponding to
                either the first or second time in the lookup.

    * heading_frequency:
        The number of lines after which the heading entries will be repeated
        (to assist in remembering column names when the output is long).  A
        value of 0 will result in no repetitions).

    * field_index:
        A list of the field indices which should be printed (defaults to all).

    * field_property:
        A dictionary specifying named criteria that a particular lookup must
        meet in order to be printed (e.g. {"lbuser4": 16004, "lbft": 3} would
        print fields with STASH 16004 at forecast time 3) (defaults to all).

"""
import os
import re
import sys
import errno
import mule
import mule.pp
import six
import numpy as np
import argparse
import textwrap
from um_utils.stashmaster import STASHmaster
from um_utils.version import report_modules
from um_utils.pumf import _banner

# The global print settings dictionary
PRINT_SETTINGS = {
    "column_names": ["index", "stash_name", "lbft", "lblev", "lbfc",
                     "lbuser4", "lbnpt", "lbrow", "t1"],
    "heading_frequency": 100,
    "field_index": [],
    "field_property": {},
    }


def field_summary(umf, stdout=None, **kwargs):
    """
    Print a summary of the field headers from a given file.

    Args:
        * umf:
            The :class:`UMFile` instance to summarise.

    Kwargs:
        * stdout:
            The open file-like object to write the output to, default
            is to use sys.stdout.

    Other Kwargs:
        Any other keywords are assumed to be settings to override
        the values in the global PRINT_SETTINGS dictionary, see
        the docstring of the :mod:`summary` module for details

    """
    # Setup output
    if stdout is None:
        stdout = sys.stdout

    # A banner to report the filename
    stdout.write(_banner("SUMMARY Report")+"\n")
    stdout.write("File: {0}\n\n".format(umf._source_path))

    # Deal with the possible keywords - take the global print settings
    # dictionary as a starting point and add any changes supplied in
    # the call to this method
    print_settings = PRINT_SETTINGS.copy()
    for keyword, value in kwargs.items():
        if keyword in print_settings:
            print_settings[keyword] = value
        else:
            msg = "Keyword not recognised: {0}"
            raise ValueError(msg.format(keyword))

    # Retrieve the settings from the settings dictionary
    field_index = print_settings["field_index"]
    field_property = print_settings["field_property"]
    heading_frequency = print_settings["heading_frequency"]
    properties = print_settings["column_names"]

    # Summary cannot handle empty field entrys
    umf.remove_empty_lookups()

    # Get the fields (filter by index if requested)
    fields = umf.fields
    if field_index != []:
        fields = [fields[ind] for ind in field_index]

    # And filter by property
    if field_property != {}:
        for prop, value in six.iteritems(field_property):
            fields = [field for field in fields
                      if getattr(field, prop) == value]

    # If the filtering was too agressive, exit here
    if len(fields) == 0:
        msg = "No fields found in file after filtering"
        raise ValueError(msg)

    # Find a field reference with full property names (to save time)
    ref_field = None
    for field in fields:
        if field.lbrel in (2, 3):
            ref_field = field
            break
    if ref_field is None:
        msg = ("Cannot find a field in the file with a header "
               "release number of 2 or 3")
        raise ValueError(msg)

    # Use this reference field to convert the list of properties to a list
    # of indices
    indices = []
    stash_name_index = None
    index_name_index = None
    t1_name_index = None
    t2_name_index = None
    for iprop, prop in enumerate(properties):
        for name, index in ref_field.HEADER_MAPPING:
            if name == prop:
                indices.append(index)
        # Pickup the special request for the stash name; set the index here
        # to zero which will safely return "None" from the actual field, but
        # save the index in the indices array for use later
        if prop == "stash_name":
            indices.append(0)
            stash_name_index = iprop
        # The index name picks up the field index
        if prop == "index":
            indices.append(0)
            index_name_index = iprop
        # The t1 name picks up the first time
        if prop == "t1":
            indices.append(0)
            t1_name_index = iprop
        # The t2 name picks up the second time
        if prop == "t2":
            indices.append(0)
            t2_name_index = iprop

    # Setup the sizes leaving space for heading lines
    if heading_frequency <= 0:
        heading_frequency = len(fields)
    total_headings = len(fields)//heading_frequency + 1
    total_lines = len(fields) + total_headings*3

    # Create array with one entry for each requested property, for each field
    array = np.empty((total_lines, len(properties)), dtype=object)

    # This array will store the maximum width of each column as it is
    # generated, for use in the formatting later
    element_widths = np.zeros(array.shape, dtype="i4")

    # Now go through the fields, grabbing the requested indices from the
    # lookup array...
    array_ind = 0
    for ifield, field in enumerate(fields):
        # Leave a gap for a heading later
        if ifield % heading_frequency == 0:
            array_ind += 3

        array[array_ind] = [str(item) for item in field.raw[indices]]

        # If the stash name was requested, get it here (if possible)
        if stash_name_index is not None:
            if field.stash is not None:
                stash_name = field.stash.name
            else:
                stash_name = "UNKNOWN STASH CODE"
            array[array_ind][stash_name_index] = stash_name

        # If the index was requested, get it here
        if index_name_index is not None:
            array[array_ind][index_name_index] = str(ifield + 1)

        # If the t1 time was requested, get it here
        time_format = "{0:04d}/{1:02d}/{2:02d} {3:02d}:{4:02d}:{5:02d}"
        if t1_name_index is not None:
            array[array_ind][t1_name_index] = (
                time_format.format(*field.raw[1:7]))

        # If the t1 time was requested, get it here
        if t2_name_index is not None:
            array[array_ind][t2_name_index] = (
                time_format.format(*field.raw[7:13]))

        # Save the widths of each element to the width array
        element_widths[array_ind] = [len(item) for item in array[array_ind]]

        # Increment the index
        array_ind += 1

    # Can now calculate the maximum width needed for each column
    max_widths = np.max(element_widths, axis=0)

    # Make sure the columns also have space for the headings
    for iprop, prop in enumerate(properties):
        # Leave extra space for the first name (to insert a # character)
        proplen = len(prop)
        if iprop == 0:
            proplen += 2
        if max_widths[iprop] < proplen:
            max_widths[iprop] = proplen

    # Generate format strings for the output function; the headings
    # will be the same width as the columns but will be left-justified
    col_format = ["{" + ":>{0}s".format(width) + "}" for width in max_widths]

    # Also left justify the stash name if it is there (it looks better)
    if stash_name_index is not None:
        col_format[stash_name_index] = (
            "{" + ":<{0}s".format(max_widths[stash_name_index]) + "}")

    # Create an array from the heading names - add a hash character to the
    # first one (makes it easier to identify heading lines)
    headings = np.array(["# "+properties[0]] + properties[1:],
                        dtype="U", ndmin=2)

    # Add a dividing line; this will just be dashes the same width as the
    # column entries.  Insert a hash into the first entry as with the names.
    div = ["-"*width for width in max_widths]
    div[0] = div[0].replace('--', '# ', 1)
    divider = np.array(div, dtype="U", ndmin=2)

    # Insert the heading lines into the array
    for ihead in range(total_headings):
        array[(3 + heading_frequency)*ihead] = divider
        array[(3 + heading_frequency)*ihead + 1] = headings
        array[(3 + heading_frequency)*ihead + 2] = divider

    output_string = " " + str.join(" | ", col_format) + " \n"

    # Finally output the entire array with the appropriate widths
    for line in array:
        stdout.write(output_string.format(*line))


def _main():
    """
    Main function; accepts command line arguments to override the print
    settings and provides a UM file to summarise.

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] [options] input_file

    This script will output a summary table of the lookup headers in a UM
    file, with the columns selected by the user.
    """
    title = _banner(
        "SUMMARY - Print a summary of the fields in a UM File "
        "(using the Mule API)", banner_char="=")

    # Include a list of the lookup names as they appear in Mule
    lookup_names = [name for name, _ in mule._LOOKUP_HEADER_3]
    lookup_names += [name for name, _ in mule._LOOKUP_HEADER_2
                     if name not in lookup_names]
    lookup_names = ", ".join(lookup_names)

    help_epilog = """
    possible lookup names for the column-names option:
    {0}

    for details of how these relate to indices see UMDP F03:
      https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf
    """.format(textwrap.fill(lookup_names,
                             width=80,
                             initial_indent=4*" ",
                             subsequent_indent=8*" "))

    # Setup the parser
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        epilog=textwrap.dedent(help_epilog),
        formatter_class=argparse.RawTextHelpFormatter,
        )

    # No need to output help text for hte input file (it's obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)

    parser.add_argument(
        "--column-names", metavar="--column-names name1[,name2][...]",
        help="set the names of the lookup header items to print, in the \n"
        "order the columns should appear as a comma separated list. A \n"
        "special entry of \"stash_name\" will put in the field's name \n"
        "according to the STASHmaster, \"index\" will give the field's \n"
        "index number in the file, and \"t1\" or \"t2\" will give the first \n"
        "and second time from the lookup (nicely formatted)\n ")

    parser.add_argument(
        "--heading-frequency", metavar="N", type=int,
        help="repeat the column heading block every N lines (to avoid \n"
        "having to scroll too far to identify columns in the output) A \n"
        "value of 0 means do not repeat the heading block\n ")

    parser.add_argument(
        "--field-index", metavar="i1[,i2][,i3:i5][...]",
        help="limit the output to specific fields by index (comma-separated \n"
        "list of single indices, or ranges of indices separated by a single \n"
        "colon-character)\n ")

    parser.add_argument(
        "--field-property", metavar="key1=value1[,key2=value2][...]",
        help="limit the output to specific fields using a property string \n"
        "(comma-separated list of key=value pairs where key is the name of \n"
        "a lookup property and value is what it must be set to)\n ")

    parser.add_argument(
        "--stashmaster",
        help="either the full path to a valid stashmaster file, or a UM \n"
        "version number e.g. '10.2'; if given a number summary will look in \n"
        "the path defined by: \n"
        "  mule.stashmaster.STASHMASTER_PATH_PATTERN \n"
        "which by default is : \n"
        "  $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A\n")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(SUMMARY) Module Information")),
    report_modules()
    print("")

    # Process column names
    if args.column_names is not None:
        properties = args.column_names.split(",")
        PRINT_SETTINGS["column_names"] = properties

    # Process field filtering by index argument
    field_index = []
    if args.field_index is not None:
        for arg in args.field_index.split(","):
            if re.match(r"^\d+$", arg):
                field_index.append(int(arg))
            elif re.match(r"^\d+:\d+$", arg):
                field_index += range(*[int(elt) for elt in arg.split(":")])
            else:
                msg = "Unrecognised field index option: {0}"
                raise ValueError(msg.format(arg))
    PRINT_SETTINGS["field_index"] = field_index

    # Process field filtering by property argument
    field_property = {}
    if args.field_property is not None:
        for arg in args.field_property.split(","):
            if re.match(r"^\w+=\d+$", arg):
                name, value = arg.split("=")
                field_property[name] = int(value)
            else:
                msg = "Unrecognised field property option: {0}"
                raise ValueError(msg.format(arg))
    PRINT_SETTINGS["field_property"] = field_property

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

    # Process heading lines
    if args.heading_frequency is not None:
        PRINT_SETTINGS["heading_frequency"] = args.heading_frequency

    # Get the filename and load it using Mule
    filename = args.input_file

    if os.path.exists(filename):
        # Check if this is a pp file
        if mule.pp.file_is_pp_file(filename):
            # Make an empty fieldsfile object and attach the pp file's
            # field objects to it
            um_file = mule.FieldsFile()
            um_file.fields = mule.pp.fields_from_pp_file(filename)
            um_file._source_path = filename
            if stashm is not None:
                um_file.attach_stashmaster_info(stashm)
            # Override the component filter as only the lookup is
            # available in a pp file
            PRINT_SETTINGS["component_filter"] = ["lookup"]
        else:
            um_file = mule.load_umfile(filename, stashmaster=stashm)

        # Now print the object to stdout, if a SIGPIPE is received handle
        # it appropriately
        try:
            field_summary(um_file)
        except IOError as error:
            if error.errno != errno.EPIPE:
                raise
    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)

if __name__ == "__main__":
    _main()
