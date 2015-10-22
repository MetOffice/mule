# (C) Crown Copyright 2015, Met Office. All rights reserved.
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
import os
import re
import sys
import errno
import mule
import numpy as np
import argparse
from um_utils.stashmaster import STASHmaster

PRINT_SETTINGS = {
    "stashmaster": None,
    "column_names": ["index",
                     "stash_name",
                     "lbft",
                     "lblev",
                     "lbfc",
                     "lbuser4",
                     "lbnpt",
                     "lbrow",
                     "t1",
                     ],
    "field_index": [],
    "field_property": {},
    "heading_frequency": 100,
    }

def field_summary(umf, properties=None, stdout=sys.stdout):
    """
    Print a summary of the field headers from a given file.

    Args:
        * umf:
            The :class:`UMFile` instance to summarise.

    Kwargs:
        * properties:
            A list containing the names of the properties making
            up each column in the summary.
        * stdout:
            A (open) file-like object to write the summary to.
    
    """
    # Retrieve the settings from the global dictionary
    field_index = PRINT_SETTINGS["field_index"]
    field_property = PRINT_SETTINGS["field_property"]
    stashmaster = PRINT_SETTINGS["stashmaster"]
    heading_frequency = PRINT_SETTINGS["heading_frequency"]

    # Setup the STASHmaster; if the user didn't supply an override
    # try to take the version from the file:
    stashm = None
    if stashmaster is None:
        um_int_version = umf.fixed_length_header.model_version
        if um_int_version != umf.fixed_length_header.MDI:
            um_version = "vn{0}.{1}".format(um_int_version // 100,
                                            um_int_version % 10)
            stashm = STASHmaster(version=um_version)
    else:
        if os.path.exists(stashmaster):
            stashm = STASHmaster(fname=stashmaster)
        else:
            stashm = STASHmaster(version=stashmaster)

    # Summary cannot handle empty field entrys
    umf.remove_empty_lookups()

    if properties is None:
        if PRINT_SETTINGS["column_names"] is None:
            msg = "No column names provided"
            raise ValueError(msg)
        properties = PRINT_SETTINGS["column_names"]        

    # Get the fields (filter by index if requested)
    fields = umf.fields
    if field_index != []:
        fields = [fields[ind] for ind in field_index]

    # And filter by property
    if field_property != {}:
        for prop, value in field_property.iteritems():
            fields = [field for field in fields
                      if getattr(field, prop) == value]

    # If the filtering was too agressive, exit here
    if len(fields) == 0:
        msg = "No fields found in file after filtering"
        raise ValueError(msg)

    # Find a field reference with full property names (to save time)
    ref_field = None
    for field in fields:
        if field.lbrel in (2,3):
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

        array[array_ind] = map(str, field.raw[indices])
        
        # If the stash name was requested, get it here (if possible)
        if stash_name_index is not None:
            if stashm.has_key(field.lbuser4):
                stash_name = stashm[field.lbuser4].name
            else:
                stash_name = "UNKNOWN STASH CODE"
            array[array_ind][stash_name_index] = stash_name

        # If the index was requested, get it here
        if index_name_index is not None:
            array[array_ind][index_name_index] = str(ifield + 1)

        # If the t1 time was requested, get it here
        if t1_name_index is not None:
            array[array_ind][t1_name_index] = (
                "{0:04d}/{1:02d}/{2:02d} {3:02d}:{4:02d}:{5:02d}"
                .format(*field.raw[1:7]))
            
        # If the t1 time was requested, get it here
        if t2_name_index is not None:
            array[array_ind][t2_name_index] = (
                "{0:04d}/{1:02d}/{2:02d} {3:02d}:{4:02d}:{5:02d}"
                .format(*field.raw[7:13]))
            
        # Save the widths of each element to the width array
        element_widths[array_ind] = map(len, array[array_ind])

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

    # Generate format strings for numpy's savetxt function; the headings
    # will be the same width as the columns but will be left-justified
    col_format = [" %{0}s ".format(width) for width in max_widths]

    # Also left justify the stash name if it is there (it looks better)
    if stash_name_index is not None:
        col_format[stash_name_index] = (
            " %-{0}s ".format(max_widths[stash_name_index]))

    # Create an array from the heading names - add a hash character to the
    # first one (makes it easier to identify heading lines)
    properties[0] = "# "+properties[0]
    headings = np.array(properties, dtype="S", ndmin=2)

    # Add a dividing line; this will just be dashes the same width as the
    # column entries.  Insert a hash into the first entry as with the names.
    div = ["-"*width for width in max_widths]    
    div[0] = div[0].replace('--', '# ', 1)
    divider = np.array(div, dtype="S", ndmin=2)

    # Insert the heading lines into the array
    for ihead in range(total_headings):
        array[(3 + heading_frequency)*ihead] = divider
        array[(3 + heading_frequency)*ihead + 1] = headings
        array[(3 + heading_frequency)*ihead + 2] = divider
        
    # Finally output the entire array with the appropriate widths
    np.savetxt(stdout, array, fmt=col_format, delimiter="|")


def _main():
    """
    Main function; accepts command line arguments to override the print
    settings and provides a UM file to print.
    
    """
    # Create a quick version of the regular raw description formatter which
    # adds spaces between the option help text
    class BlankLinesHelpFormatter(argparse.HelpFormatter):
        def _split_lines(self, text, width):
            return super(
                BlankLinesHelpFormatter, self)._split_lines(text, width) + ['']
    
    parser = argparse.ArgumentParser(
        usage="%(prog)s [options] input_file",
        description="""
        SUMMARY - Print a summary of the fields in a UM File
        (using the Mule API).

        This script will output a summary table of the lookup headers in a UM
        file, with the columns selected by the user.
        """,
        formatter_class=BlankLinesHelpFormatter,
        )
    parser.add_argument("--column-names",
                        help="set the names of the lookup header items to "
                        "print, in the order the columns should appear as a "
                        "comma separated list. A special entry of "
                        "\"stash_name\" will put in the field's name according "
                        "to the STASHmaster",
                        metavar="--column-names name1[,name2][...]",
                        )

    # No need to output help text for hte input file (it's obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)

    parser.add_argument("--heading-frequency",
                        help="repeat the column heading block every N "
                        "lines (to avoid having to scroll too far to identify "
                        "columns in the output) A value of 0 means do not "
                        "repeat the heading block",
                        metavar="N", type=int,
                        )
    parser.add_argument("--field-index",
                        help="limit the output to specific fields by index "
                        "(comma-separated list of single indices, or ranges of "
                        "indices separated by a single colon-character)",
                        metavar="i1[,i2][,i3:i5][...]",
                        )
    parser.add_argument("--field-property",
                        help="limit the output to specific fields using "
                        "a property string (comma-separated list of key=value "
                        "pairs where the key is the name of a lookup property)",
                        metavar="key1=value1[,key2=value2][...]",
                        )
    parser.add_argument("--stashmaster",
                        help="either the full path to a valid stashmaster "
                        "file, or a UM version number e.g. '10.2'; if given "
                        "a number pumf will look in the following path: "
                        "$UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A",
                        )

    args = parser.parse_args()

    # Process column names
    properties = None
    if args.column_names is not None:
        properties = args.column_names.split(",")

    # Process field filtering by index argument
    field_index = []
    if args.field_index is not None:
        for arg in args.field_index.split(","):
            if re.match(r"^\d+$", arg):
                field_index.append(int(arg))
            elif re.match(r"^\d+:\d+$", arg):
                field_index += range(*map(int, arg.split(":")))
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

    # Process stashmaster option
    if args.stashmaster is not None:
        PRINT_SETTINGS["stashmaster"] = args.stashmaster

    # Process heading lines
    if args.heading_frequency is not None:
        PRINT_SETTINGS["heading_frequency"] = args.heading_frequency

    # Get the filename and load it using Mule
    filename = args.input_file

    if os.path.exists(filename):
        um_file = mule.load_umfile(filename)
        # Now print the object to stdout, if a SIGPIPE is received handle
        # it appropriately
        try:
            field_summary(um_file, properties)
        except IOError as e:
            if e.errno != errno.EPIPE:
                raise

        
if __name__ == "__main__":
    _main()
