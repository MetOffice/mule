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

# This dictionary stores a list of global settings that control the
# printing - when called as a main program these can be overidden by
# the command line arguments, or the user can easily adjust these in
# various ways to customise their output.
PRINT_SETTINGS = {
    "skip_missing_values": True,
    "named_properties_only": True,
    "filter_names": [""],
    "component_filter": None,
    "field_index": [],
    "field_property": {},
    "headers_only": False,
    "print_columns": 1,
    "stashmaster": None,
    }


def _banner(message):
    """A simple function which returns a banner string."""
    return "{0:s}\n* {1:s} *\n{0:s}\n".format("%"*(len(message)+4),message)


def _header_to_string_1d(header):
    """
    Function which converts a header to a string (for a 1d header).

    Args:
        * header:
            A subclass of :class:`mule.BaseHeaderComponent1D`.

    """
    as_string = ""
    to_output = []
    max_width = 0
    max_val_width = 0

    # Retrieve settings from global dict
    skip_missing = PRINT_SETTINGS["skip_missing_values"]
    named_properties = PRINT_SETTINGS["named_properties_only"]
    filter_names = PRINT_SETTINGS["filter_names"]
    print_columns = PRINT_SETTINGS["print_columns"]

    if named_properties and hasattr(header, "HEADER_MAPPING"):
        # If we are only to select from named properties, use the
        # header mapping dictionary as our iterator
        for name, index in header.HEADER_MAPPING:
            value = getattr(header, name)
            # Add the value to the output list if it satisfies the
            # requirements for being missing (or not)
            if not (skip_missing and value == header.MDI):
                name = "({0}) {1}".format(index, name)
                valstr = str(value)
                to_output.append((name, valstr))
                # Also keep a running total of the longest name
                # assigned here to use later
                if max_width < len(name): max_width = len(name)
                if max_val_width < len(valstr): max_val_width = len(valstr)
    else:
        # If we are using indices iterate through the raw values
        # in the header (skip the first value, it is a dummy value)
        for index, value in enumerate(header.raw[1:]):
            # Add the value to the output list if it satisfies the
            # requirements for being missing (or not)
            if not (skip_missing and value == header.MDI):
                name = str(index + 1)
                valstr = str(value)                
                to_output.append((name, valstr))
                # Also keep a running total of the longest name
                # assigned here to use later
                if max_width < len(name): max_width = len(name)
                if max_val_width < len(valstr): max_val_width = len(valstr)                    

    # Create a formatting string for the names which adds enough
    # white-space to align the values, based on the maximum width
    # calculated in the above loop
    width_format = ("  {0:"+str(max_width)+"s} "
                    ": {1:"+str(max_val_width)+"s}")
    count = 0
    for name, value in to_output:
        # Apply the filtering based on supplied words here
        if any([filt in name for filt in filter_names]):
            as_string += width_format.format(name, value)
            count += 1
            if count % print_columns == 0:
                as_string += "\n"

    return as_string + "\n"


def _header_to_string_2d(header):
    """
    Function which converts a header to a string (for a 2d header).

    Args:
        * header:
            A subclass of :class:`mule.BaseHeaderComponent2D`.

    """    
    as_string = ""

    # Retrieve settings from global dict
    skip_missing = PRINT_SETTINGS["skip_missing_values"]
    named_properties = PRINT_SETTINGS["named_properties_only"]
    filter_names = PRINT_SETTINGS["filter_names"]
    print_columns = PRINT_SETTINGS["print_columns"]
    
    if named_properties and hasattr(header, "HEADER_MAPPING"):
        # If we are only to select from named properties, use the
        # header mapping dictionary as our iterator        
        for name, index in header.HEADER_MAPPING:
            # In the 2-d case the name filtering only really makes
            # sense for the named dimension, so apply it here
            if any([filt in name for filt in filter_names]):
                value = getattr(header, name)
                # Omit the printing of the dimension header if every
                # element in that slice is missing
                if not (skip_missing and np.all(value == header.MDI)):
                    as_string += "({0}) {1}:\n".format(index[1], name)

                # Now iterate through the individual elements in this
                # dimension to build up the output list
                to_output = []
                max_width = 0
                max_val_width = 0
                for ielement, element in enumerate(value):
                    # Add the element to the output list if it satisfies
                    # the requirements for being missing (or not)
                    if not (skip_missing and element == header.MDI):
                        name = str(ielement + 1)
                        valstr = str(element)
                        to_output.append((name, valstr))
                        # Also keep a running total of the longest name
                        # assigned here for use later
                        if max_width < len(name): max_width = len(name)
                        if max_val_width < len(valstr):
                                max_val_width = len(valstr)

                # Create a formatting string for the names which adds
                # enough white-space to align the values, based on the
                # maximum width calculated in the above loop
                width_format = ("  {0:"+str(max_width)+"s} "
                                ": {1:"+str(max_val_width)+"s}")
                for count, (name, value) in enumerate(to_output):
                    as_string += width_format.format(name, value)
                    if ((count + 1) % print_columns == 0 or
                        (count + 1) == len(to_output)):
                        as_string += "\n"

    else:
        # If we are using indices iterate through the dimensions using
        # their raw values (skip the first slice, it is a dummy value)        
        for index in range(1, header.shape[1]+1):
            value = header.raw[:, index]
            # Omit the printing of the dimension header if every
            # element in that slice is missing
            if not (skip_missing and np.all(value == header.MDI)):
                as_string += "{0}/{1}:\n".format(index, header.shape[1])

            # Now iterate through the individual elements in this
            # dimension to build up the output list
            to_output = []
            max_width = 0
            max_val_width = 0
            for ielement, element in enumerate(value):
                # Add the element to the output list if it satisfies
                # the requirements for being missing (or not)                
                if not (skip_missing and element == header.MDI):
                    name = str(ielement + 1)
                    valstr = str(element)
                    to_output.append((name, valstr))
                    # Also keep a running total of the longest name
                    # assigned here for use later                    
                    if max_width < len(name): max_width = len(name)
                    if max_val_width < len(valstr):
                        max_val_width = len(valstr)                        

            # Create a formatting string for the names which adds
            # enough white-space to align the values, based on the
            # maximum width calculated in the above loop
            width_format = ("  {0:"+str(max_width)+"s} "
                            ": {1:"+str(max_val_width)+"s}")
            for count, (name, value) in enumerate(to_output):
                as_string += width_format.format(name, value)
                if ((count + 1) % print_columns == 0 or
                    (count + 1) == len(to_output)):
                    as_string += "\n"

    return as_string + "\n"    


def _field_to_string(field):
    """
    Function which converts the lookup header from a field object to
    a string.

    Args:
        * field:
            A subclass of :class:`mule.Field`.

    """     
    as_string = ""
    to_output = []
    max_width = 0
    max_val_width = 0

    # Retrieve settings from global dict
    named_properties = PRINT_SETTINGS["named_properties_only"]
    filter_names = PRINT_SETTINGS["filter_names"]
    headers_only = PRINT_SETTINGS["headers_only"]
    print_columns = PRINT_SETTINGS["print_columns"]

    if named_properties and hasattr(field, "HEADER_MAPPING"):
        # If we are only to select from named properties, use the
        # header mapping dictionary as our iterator   
        for name, index in field.HEADER_MAPPING:
            value = getattr(field, name)
            name = "({0}) {1}".format(index, name)
            valstr = str(value)
            to_output.append((name, valstr))
            # Also keep a running total of the longest name
            # assigned here for use later               
            if max_width < len(name): max_width = len(name)
            if max_val_width < len(valstr): max_val_width = len(valstr)
    else:
        # If we are using indices iterate through the raw values
        # in the header (skip the first value, it is a dummy value)        
        for index, value in enumerate(field.raw[1:]):
            name = str(index + 1)
            valstr = str(value)
            to_output.append((name, valstr))
            # Also keep a running total of the longest name
            # assigned here for use later               
            if max_width < len(name): max_width = len(name)
            if max_val_width < len(valstr): max_val_width = len(valstr)

    if not headers_only:
        # Get the field data and calculate and extra quantities
        data = field.get_data()
        # Mask out missing values first
        masked_data = np.ma.masked_array(data, data == field.bmdi)
        for name, func in [("maximum", np.max),
                           ("minimum", np.min)]:
            valstr = str(func(masked_data))
            to_output.append((name, valstr))
            if max_width < len(name): max_width = len(name)
            if max_val_width < len(valstr): max_val_width = len(valstr)            
                
    # Create a formatting string for the names which adds
    # enough white-space to align the values, based on the
    # maximum width calculated in the above loop
    width_format = ("  {0:"+str(max_width)+"s} "
                    ": {1:"+str(max_val_width)+"s}")
    count = 0
    for name, value in to_output:
        # Apply the filtering based on supplied words here
        if any([filt in name for filt in filter_names]):
            as_string += width_format.format(name, value)
            count += 1
            if count % print_columns == 0:
                as_string += "\n"

    return as_string + "\n"


def _print_um_file(umf, stdout=sys.stdout):
    """
    Print the contents of a :class:`UMFile` object.

    Args:
        * umf:
            The UM file object to be printed.
    Kwargs:
        * stdout:
            A (open) file-like object to print to.

    """
    # Prefix the report with a banner and report the filename
    stdout.write(_banner("PUMF-II Report")+"\n")
    stdout.write("File: {0}\n\n".format(umf._source_path))
    
    # Retrieve settings from global dict
    component_filter = PRINT_SETTINGS["component_filter"]
    field_index = PRINT_SETTINGS["field_index"]
    field_property = PRINT_SETTINGS["field_property"]
    stashmaster = PRINT_SETTINGS["stashmaster"]
    
    # Create a list of component names to print, pre-pending the fixed length
    # header since we want to include it
    names = ["fixed_length_header"] + [name for name, _ in umf.COMPONENTS]

    # If the user hasn't set a component filter, set it to catch everything
    if component_filter is None:
        component_filter = names + ["lookup"]
    else:
        for name in component_filter:
            if name not in names + ["lookup"]:
                msg = ("File contains no '{0}' component")
                raise ValueError(msg.format(name))

    # Go through the components in the file
    for name in names:
        if name in component_filter:
            # Print a title banner quoting the name of the component first
            stdout.write(_banner(name))
            component = getattr(umf, name)
            if component is not None:
                # Check if the component is 1d or 2d and call the corresponding
                # method to print it (note: if the component class defined a
                # method of its own to do this it would be simpler)
                if len(component.shape) == 1:
                    stdout.write(_header_to_string_1d(component))
                elif len(component.shape) == 2:
                    stdout.write(_header_to_string_2d(component))
            else:
                # If a component is missing print a placeholder
                stdout.write(" --- \n\n")

    # Moving onto the fields
    if "lookup" in component_filter:

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
        
        total_fields = len(umf.fields)
        for ifield, field in enumerate(umf.fields):

            # Skip the field if it isn't in the index filtering
            if field_index != [] and ifield + 1 not in field_index:
                continue

            if field.lbrel != -99:
                # Skip the field if it doesn't match the property filtering
                if field_property != {}:
                    skip_field = False
                    for prop, value in field_property.iteritems():
                        field_val = getattr(field, prop, None)
                        if field_val is not None and field_val != value:
                            skip_field = True
                            break
                    if skip_field:
                        continue

                # Try to include the STASH name of the field in the banner, as well
                # as the Field's index in the context of the total fields in the file
                heading = "Field {0}/{1} ".format(ifield+1, total_fields)
                if stashm is not None and stashm.has_key(field.lbuser4):
                    heading += "- " + stashm[field.lbuser4].name
                stdout.write(_banner(heading))
                # Print the header (note: as with the components, if the Field class
                # defined such a method we could call it here instead)
                stdout.write(_field_to_string(field))


def pprint(um_object, stdout=sys.stdout):
    """
    Given a recognised object, print it using an appropriate method.

    Args:
        * um_object:
            A UM object of one of the following subclasses:
              * :class:`mule.BaseHeaderComponent`
              * :class:`mule.UMFile`
              * :class:`mule.Field`
    
    """
    if isinstance(um_object, mule.BaseHeaderComponent1D):
        stdout.write(_header_to_string_1d(um_object))
    elif isinstance(um_object, mule.BaseHeaderComponent2D):
        stdout.write(_header_to_string_2d(um_object))
    elif isinstance(um_object, mule.Field):
        stdout.write(_field_to_string(um_object))
    elif isinstance(um_object, mule.UMFile):
        _print_um_file(um_object, stdout)
    else:
        msg = "Unrecognised object type: {0}"
        raise ValueError(msg.format(type(um_object)))


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
        usage="%(prog)s [options] input_filename",
        description="""
        PUMF-II - Pretty Printer for UM Files, version II (using the Mule API).

        This script will output the contents of the headers from a UM file
        to stdout.  The default output may be customised with a variety
        of options (see below).  
        """,
        formatter_class=BlankLinesHelpFormatter,
        )

    # No need to output help text for the input file (it's obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)
    
    parser.add_argument("--include-missing",
                        help="include header values which are set to MDI",
                        action="store_true")
    parser.add_argument("--use-indices",
                        help="list headers by their indices (instead of only "
                        "listing named headers)",
                        action="store_true")
    parser.add_argument("--headers-only",
                        help="only list headers (do not read data and calculate "
                        "any derived statistics)",
                        action="store_true")
    parser.add_argument("--components",
                        help="limit the header output to specific components "
                        "(comma-separated list of component names, with no "
                        "spaces)",
                        metavar="component1[,component2][...]")
    parser.add_argument("--field-index",
                        help="limit the lookup output to specific fields by index "
                        "(comma-separated list of single indices, or ranges of "
                        "indices separated by a single colon-character)",
                        metavar="i1[,i2][,i3:i5][...]")
    parser.add_argument("--field-property",
                        help="limit the lookup output to specific field using "
                        "a property string (comma-separated list of key=value "
                        "pairs where the key is the name of a lookup property)",
                        metavar="key1=value1[,key2=value2][...]")
    parser.add_argument("--print-only",
                        help="only print properties (after filtering) which "
                        "contain a specific word (comma-separated list of words "
                        "which must be in properties to be printed)",
                        metavar="word1[,word2][...]")
    parser.add_argument("--print-columns",
                        help="how many columns should be printed in the output",
                        metavar="N")
    parser.add_argument("--stashmaster",
                        help="either the full path to a valid stashmaster "
                        "file, or a UM version number e.g. '10.2'; if given "
                        "a number pumf will look in the following path: "
                        "$UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A")

    args = parser.parse_args()

    # Process component filtering argument
    if args.components is not None:
        PRINT_SETTINGS["component_filter"] = (
            args.components.split(","))

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

    # Process print filtering
    if args.print_only is not None:
        PRINT_SETTINGS["filter_names"] = (
            args.print_only.split(","))

    # Process remaining options
    if args.print_columns is not None:
        PRINT_SETTINGS["print_columns"] = int(args.print_columns)
    if args.stashmaster is not None:
        PRINT_SETTINGS["stashmaster"] = args.stashmaster
    if args.include_missing:
        PRINT_SETTINGS["skip_missing_values"] = False
    if args.use_indices:
        PRINT_SETTINGS["named_properties_only"] = False
    if args.headers_only:
        PRINT_SETTINGS["headers_only"] = True

    # Get the filename and load it using Mule
    filename = args.input_file
    if os.path.exists(filename):
        um_file = mule.load_umfile(filename)
        # Now print the object to stdout, if a SIGPIPE is received handle
        # it appropriately
        try:
            pprint(um_file)
        except IOError as e:
            if e.errno != errno.EPIPE:
                raise
    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)


if __name__ == "__main__":
    _main()
