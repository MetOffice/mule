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

unpack is a simple utility to unpack WGDOS data in a supplied packed Fieldsfile

Usage:

* Take a :class:`mule.FieldsFile` object and return a :class:`mule.FieldsFile`
   object that has been unpacked.

   >>> fieldsfile_object = unpack.unpack(umfile_object)

"""

import os
import sys
import argparse
import textwrap
import mule
import mule.pp
from um_utils.version import report_modules
from um_utils.pumf import _banner


def unpack(origfile):
    """
    Given a filesfile file as a FieldsFile object
    return an unpacked FieldsFile object.

    Args:
        * origfile:
            A :class:`mule.FieldsFile` object.

    """
    # Copy the original file
    unpackedfile = origfile.copy()

    # if field is wgdos packed, unpack it
    for field in origfile.fields:
        if field.lbrel in (2, 3) and field.lbpack == 1:
            field.lbpack = 0
        unpackedfile.fields.append(field)

    return unpackedfile


def _main():
    """
    Main function; accepts command line argument for paths to
    the input and output files.

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] input_filename output_filename

    This script will write a new file where all WGDOS packed fields in the
    original are replaced by unpacked fields.
    """
    title = _banner(
        "UNPACK - Unpacks WGDOS packed fields in a UM FieldsFile "
        "(Using the Mule API)", banner_char="=")

    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,
        )

    # No need to output help text for the input files (it's obvious)
    parser.add_argument("input_filename", help=argparse.SUPPRESS)
    parser.add_argument("output_filename", help=argparse.SUPPRESS)

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(UNPACK) Module Information")),
    report_modules()
    print("")

    input_filename = args.input_filename
    if not os.path.exists(input_filename):
        msg = "File not found: {0}".format(input_filename)
        raise ValueError(msg)

    output_filename = args.output_filename

    # Check if the file is a pp file
    pp_mode = mule.pp.file_is_pp_file(input_filename)
    if pp_mode:
        # Make an empty fieldsfile object and attach the pp file's
        # field objects to it
        origfile = mule.FieldsFile()
        origfile.fields = mule.pp.fields_from_pp_file(input_filename)
        origfile._source_path = input_filename
    else:
        # Read in file as a FieldsFile
        origfile = mule.FieldsFile.from_file(input_filename)

    # Unpack fieldsfile
    unpackedfile = unpack(origfile)

    # Write file
    if pp_mode:
        mule.pp.fields_to_pp_file(output_filename, unpackedfile.fields)
    else:
        unpackedfile.to_file(output_filename)


if __name__ == "__main__":
    _main()
