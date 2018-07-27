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
PUMF (Print UM FieldsFiles) is a utility to assist in examining UM files.

Usage:

 * Pretty-print an entire :class:`mule.UMFile` object:

    >>> pumf.pprint(umfile_object)

 * You can also print individual components or fields:

    >>> pumf.pprint(umfile_object.fixed_length_header)

    >>> pumf.pprint(umfile_object.fields[0])

Global print settings:

    The module contains a global "PRINT_SETTINGS" dictionary, which defines
    default values for the various options; these may be overidden for an
    entire script/session if desired, or in a startup file e.g.

    >>> from um_utils import pumf
    >>> pumf.PRINT_SETTINGS["print_columns"] = 4

    Alternatively each of these settings may be supplied to the main "pprint"
    routine as keyword arguments.  The available settings are:

    * include_missing:
        Flag to indicate whether or not pumf should print header values which
        are set to the "MDI" value of the header in question.  This will also
        cause pumf not to print entries for components that do not exist in
        the file (default: False).

    * use_indices:
        Flag to indicate whether pumf should only print out named properties
        (these are any with an entry in the "HEADER_MAPPING" definition for
        the given component) (default: True).

    * headers_only:
        Flag to indicate whether to restrict the printing to header values
        only (normally pumf will also read the data and print some statistical
        information as well) (default: False).

    * print_columns:
        Indicates how many columns to use for the output (default: 1).

    * component_filter:
        A list of header component names which should be included in the
        output (e.g. ["fixed_length_header", "lookup"]), (defaults to all).

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
import six
import errno
import mule
import mule.pp
import numpy as np
import argparse
import textwrap
from um_utils.stashmaster import STASHmaster
from um_utils.version import report_modules

# The global print settings dictionary
PRINT_SETTINGS = {
    "include_missing": False,
    "use_indices": False,
    "headers_only": False,
    "print_columns": 1,
    "component_filter": None,
    "field_index": [],
    "field_property": {},
    }


def _banner(message, banner_char="%"):
    """A simple function which returns a banner string."""
    return "{0:s}\n* {1:s} *\n{0:s}\n".format(
        banner_char*(len(message)+4), message)


def _print_name_value_pairs(
        pairings, name_width, value_width, n_columns, stdout):
    """
    Helper function for controlled printing of a set of name, value pairs.

    Args:
        * pairings:
            Tuple pairs of the name and value to print.
        * name_width:
            The fixed-width to use for the names.
        * value_width:
            The fixed-width to use for the values.
        * n_columns:
            How many columns to print before inserting a line break.
        * stdout:
            The (open) file object to print to.

    """
    # Create a width formatting string from the given widths
    width_format = ("  {0: <"+str(name_width)+"s} "
                    ": {1: >"+str(value_width)+"s}")
    # Now print each pairing
    column_count = 0
    for name, value in pairings:
        stdout.write(width_format.format(name, value))
        # Insert a newline based on the desired column count
        column_count += 1
        if column_count % n_columns == 0:
            stdout.write("\n")
        else:
            if len(pairings) > column_count:
                stdout.write("   | ")

    # The way the above works, if the entries didn't fall nicely
    # into the number of columns, it won't end in a newline, so
    # we insert one here
    if column_count % n_columns != 0:
        if len(pairings) > n_columns:
            stdout.write("   |")
        stdout.write("\n")

    # And a final newline to break for the next section
    stdout.write("\n")


def _print_component_1d(header, stdout, print_settings=PRINT_SETTINGS):
    """
    Print function for a 1d header component.

    Args:
        * header:
            A subclass of :class:`mule.BaseHeaderComponent1D`.
    Kwargs:
        * stdout:
            A (open) file-like object to write the output to.

    """
    # Retrieve settings from global dict
    include_missing = print_settings["include_missing"]
    use_indices = print_settings["use_indices"]
    print_columns = print_settings["print_columns"]

    # The strings to print will be gathered first and then printed,
    # to allow gathering of some maximum widths for formatting
    to_output = []
    max_width = 0
    max_val_width = 0

    if not use_indices and hasattr(header, "HEADER_MAPPING"):
        # If we are only to select from named properties, use the
        # header mapping dictionary as our iterator
        for name, index in header.HEADER_MAPPING:
            try:
                value = getattr(header, name)
            except IndexError:
                value = 'Not found in file'
            # If this value is missing and we are not including missing
            # values, skip it
            if value == header.MDI and not include_missing:
                continue
            name = "({0}) {1}".format(index, name)
            valstr = str(value)
            to_output.append((name, valstr))
            # Also keep a running total of the maximum widths
            max_width = max(max_width, len(name))
            max_val_width = max(max_val_width, len(valstr))
    else:
        # If we are using indices iterate through the raw values
        # in the header (skip the first value, it is a dummy value)
        for index, value in enumerate(header.raw[1:]):
            # If this value is missing and we are not including missing
            # values, skip it
            if value == header.MDI and not include_missing:
                continue
            name = str(index + 1)
            valstr = str(value)
            to_output.append((name, valstr))
            # Also keep a running total of the maximum widths
            max_width = max(max_width, len(name))
            max_val_width = max(max_val_width, len(valstr))

    # Can now print the values using controlled widths
    _print_name_value_pairs(to_output, max_width, max_val_width,
                            print_columns, stdout)


def _print_component_2d(header, stdout, print_settings=PRINT_SETTINGS):
    """
    Print function for a 2d header component.

    Args:
        * header:
            A subclass of :class:`mule.BaseHeaderComponent2D`.
    Kwargs:
        * stdout:
            A (open) file-like object to write the output to.

    """
    # Retrieve settings from global dict
    include_missing = print_settings["include_missing"]
    use_indices = print_settings["use_indices"]
    print_columns = print_settings["print_columns"]

    if not use_indices and hasattr(header, "HEADER_MAPPING"):
        # If we are only to select from named properties, use the
        # header mapping dictionary as our iterator
        for name, index in header.HEADER_MAPPING:
            try:
                value = getattr(header, name)
            except IndexError:
                value = ['Not found in file', ]
            # Omit the printing of the header if every element in that
            # slice is missing
            if np.all(value == header.MDI) and not include_missing:
                continue
            stdout.write("({0}) {1}:\n".format(index[1], name))

            # Now iterate through the individual elements in this
            # dimension to build up the output list
            to_output = []
            max_width = 0
            max_val_width = 0
            for ielement, element in enumerate(value):
                # If this value is missing and we are not including missing
                # values, skip it
                if element == header.MDI and not include_missing:
                    continue
                name = str(ielement + 1)
                valstr = str(element)
                to_output.append((name, valstr))
                # Also keep a running total of the maximum widths
                max_width = max(max_width, len(name))
                max_val_width = max(max_val_width, len(valstr))

            # Can now print the values using controlled widths
            _print_name_value_pairs(to_output, max_width, max_val_width,
                                    print_columns, stdout)

    else:
        # If we are using indices iterate through the dimensions using
        # their raw values (skip the first slice, it is a dummy value)
        for index in range(1, header.shape[1]+1):
            value = header.raw[:, index]
            # Omit the printing of the dimension header if every
            # element in that slice is missing
            if np.all(value == header.MDI) and not include_missing:
                continue
            stdout.write("{0}/{1}:\n".format(index, header.shape[1]))

            # Now iterate through the individual elements in this
            # dimension to build up the output list
            to_output = []
            max_width = 0
            max_val_width = 0
            for ielement, element in enumerate(value):
                # If this value is missing and we are not including missing
                # values, skip it
                if element == header.MDI and not include_missing:
                    continue
                name = str(ielement + 1)
                valstr = str(element)
                to_output.append((name, valstr))
                # Also keep a running total of the maximum widths
                max_width = max(max_width, len(name))
                max_val_width = max(max_val_width, len(valstr))

            # Can now print the values using controlled widths
            _print_name_value_pairs(to_output, max_width, max_val_width,
                                    print_columns, stdout)


def _print_field(field, stdout, print_settings=PRINT_SETTINGS):
    """
    Print function for fields; prints values from the header and some
    information calculated from the data.

    Args:
        * field:
            A subclass of :class:`mule.Field`.
        * stdout:
            A (open) file-like object to write the output to.

    """
    to_output = []
    max_width = 0
    max_val_width = 0

    # Retrieve settings from global dict
    use_indices = print_settings["use_indices"]
    headers_only = print_settings["headers_only"]
    print_columns = print_settings["print_columns"]

    if not use_indices and hasattr(field, "HEADER_MAPPING"):
        # If we are only to select from named properties, use the
        # header mapping dictionary as our iterator
        for name, index in field.HEADER_MAPPING:
            value = getattr(field, name)
            name = "({0}) {1}".format(index, name)
            valstr = str(value)
            to_output.append((name, valstr))
            # Also keep a running total of the longest name
            # assigned here for use later
            max_width = max(max_width, len(name))
            max_val_width = max(max_val_width, len(valstr))
    else:
        # If we are using indices iterate through the raw values
        # in the header (skip the first value, it is a dummy value)
        for index, value in enumerate(field.raw[1:]):
            name = str(index + 1)
            valstr = str(value)
            to_output.append((name, valstr))
            # Also keep a running total of the longest name
            # assigned here for use later
            max_width = max(max_width, len(name))
            max_val_width = max(max_val_width, len(valstr))

    if not headers_only:
        # Get the field data and calculate and extra quantities
        data = field.get_data()
        # Mask out missing values first
        if hasattr(field, "bmdi"):
            masked_data = np.ma.masked_array(data, data == field.bmdi)
        else:
            masked_data = data

        for name, func in [("maximum", np.max),
                           ("minimum", np.min)]:
            valstr = str(func(masked_data))
            to_output.append((name, valstr))
            max_width = max(max_width, len(name))
            max_val_width = max(max_val_width, len(valstr))

    # Can now print the values using controlled widths
    _print_name_value_pairs(to_output, max_width, max_val_width,
                            print_columns, stdout)


def _print_um_file(umf, stdout=sys.stdout, print_settings=PRINT_SETTINGS):
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
    component_filter = print_settings["component_filter"]
    field_index = print_settings["field_index"]
    field_property = print_settings["field_property"]
    include_missing = print_settings["include_missing"]

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
            component = getattr(umf, name)
            if component is not None:
                # Check if the component is 1d or 2d and call the corresponding
                # method to print it (note: if the component class defined a
                # method of its own to do this it would be simpler)
                stdout.write(_banner(name))
                if len(component.shape) == 1:
                    _print_component_1d(component, stdout, print_settings)
                elif len(component.shape) == 2:
                    _print_component_2d(component, stdout, print_settings)
            else:
                # If a component is missing print a placeholder, unless the
                # skip_missing option is set
                if include_missing:
                    stdout.write(_banner(name))
                    stdout.write(" --- \n\n")

    # Moving onto the fields
    if "lookup" in component_filter:

        total_fields = len(umf.fields)
        for ifield, field in enumerate(umf.fields):

            # Skip the field if it isn't in the index filtering
            if field_index != [] and ifield + 1 not in field_index:
                continue

            if field.lbrel != -99:
                # Skip the field if it doesn't match the property filtering
                if field_property != {}:
                    skip_field = False
                    for prop, value in six.iteritems(field_property):
                        field_val = getattr(field, prop, None)
                        if field_val is not None and field_val != value:
                            skip_field = True
                            break
                    if skip_field:
                        continue

                # Try to include the STASH name of the field in the banner,
                # as well as the Field's index in the context of the total
                # fields in the file
                heading = "Field {0}/{1} ".format(ifield+1, total_fields)
                if field.stash is not None:
                    heading += "- " + field.stash.name
                stdout.write(_banner(heading))
                # Print the header (note: as with the components, if the
                # Field class defined such a method we could call it here
                # instead)
                _print_field(field, stdout, print_settings)


def pprint(um_object, stdout=None, **kwargs):
    """
    Given a recognised object, print it using an appropriate method.

    Args:
        * um_object:
            A UM object of one of the following subclasses:
              * :class:`mule.BaseHeaderComponent`
              * :class:`mule.UMFile`
              * :class:`mule.Field`
    Kwargs:
        * stdout:
            The open file-like object to write the output to, default
            is to use sys.stdout.

    Other Kwargs:
        Any other keywords are assumed to be settings to override
        the values in the global PRINT_SETTINGS dictionary, see
        the docstring of the :mod:`pumf` module for details

    """
    # Setup output
    if stdout is None:
        stdout = sys.stdout

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

    # Now select an appropriate print method
    if isinstance(um_object, mule.BaseHeaderComponent1D):
        _print_component_1d(um_object, stdout, print_settings)
    elif isinstance(um_object, mule.BaseHeaderComponent2D):
        _print_component_2d(um_object, stdout, print_settings)
    elif isinstance(um_object, mule.Field):
        _print_field(um_object, stdout, print_settings)
    elif isinstance(um_object, mule.UMFile):
        _print_um_file(um_object, stdout, print_settings)
    else:
        msg = "Unrecognised object type: {0}"
        raise ValueError(msg.format(type(um_object)))


def _main():
    """
    Main function; accepts command line arguments to override the print
    settings and provides a UM file to print.

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] [options] input_filename

    This script will output the contents of the headers from a UM file to
    stdout.  The default output may be customised with a variety of options
    (see below).
    """
    title = _banner(
        "PUMF-II - Pretty Printer for UM Files, version II "
        "(using the Mule API)", banner_char="=")

    # Include a list of the component names as they appear in Mule
    component_names = ", ".join(
        (["fixed_length_header"] +
         [name for name, _ in mule.UMFile.COMPONENTS] +
         ["lookup"]))

    lookup_names = [name for name, _ in mule._LOOKUP_HEADER_3]
    lookup_names += [name for name, _ in mule._LOOKUP_HEADER_2
                     if name not in lookup_names]
    lookup_names = ", ".join(lookup_names)

    help_epilog = """
    possible component names for the component option:
    {0}

    possible lookup names for the field-property option:
    {1}

    for details of how these relate to indices see UMDP F03:
      https://code.metoffice.gov.uk/doc/um/latest/papers/umdp_F03.pdf
    """.format(textwrap.fill(component_names,
                             width=80,
                             initial_indent=4*" ",
                             subsequent_indent=8*" "),
               textwrap.fill(lookup_names,
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

    # No need to output help text for the input file (it's obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)

    parser.add_argument(
        "--include-missing",
        help="include header values which are set to MDI and entries for \n"
        "components which are not present in the file (by default this will \n"
        "be hidden)\n ",
        action="store_true")
    parser.add_argument(
        "--use-indices",
        help="list headers by their indices (instead of only listing named \n"
        "headers)\n ",
        action="store_true")
    parser.add_argument(
        "--headers-only",
        help="only list headers (do not read data and calculate any derived \n"
        "statistics)\n",
        action="store_true")
    parser.add_argument(
        "--components",
        help="limit the header output to specific components \n"
        "(comma-separated list of component names, with no spaces)\n ",
        metavar="component1[,component2][...]")
    parser.add_argument(
        "--field-index",
        help="limit the lookup output to specific fields by index \n"
        "(comma-separated list of single indices, or ranges of indices \n"
        "separated by a single colon-character)\n ",
        metavar="i1[,i2][,i3:i5][...]")
    parser.add_argument(
        "--field-property",
        help="limit the lookup output to specific field using a property \n"
        "string (comma-separated list of key=value pairs where the key is \n"
        "the name of a lookup property and the value is the value it must \n"
        "take)\n ",
        metavar="key1=value1[,key2=value2][...]")
    parser.add_argument(
        "--print-columns",
        help="how many columns should be printed\n ",
        metavar="N")
    parser.add_argument(
        "--stashmaster",
        help="either the full path to a valid stashmaster file, or a UM \n"
        "version number e.g. '10.2'; if given a number pumf will look in \n"
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
    print(_banner("(PUMF-II) Module Information")),
    report_modules()
    print("")

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
                field_index += range(*[int(elt) for elt in arg.split(":")])
            else:
                msg = "Unrecognised field-index option: {0}"
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
                msg = "Unrecognised field-property option: {0}"
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

    # Process remaining options
    if args.print_columns is not None:
        PRINT_SETTINGS["print_columns"] = int(args.print_columns)
    if args.include_missing:
        PRINT_SETTINGS["include_missing"] = True
    if args.use_indices:
        PRINT_SETTINGS["use_indices"] = True
    if args.headers_only:
        PRINT_SETTINGS["headers_only"] = True

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
            pprint(um_file)
        except IOError as error:
            if error.errno != errno.EPIPE:
                raise
    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)


if __name__ == "__main__":
    _main()
