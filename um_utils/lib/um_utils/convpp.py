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
Utility for converting a UM FieldsFile, Dump or Ancil to PP format.
Able to make use of the optional "um_ppibm" extension to write the
output file in IBM format if desired (and if the "um_ppibm" module
is available)

"""
import sys
import mule
import mule.pp
import argparse
import textwrap
from um_utils.pumf import pprint, _banner
from um_utils.version import report_modules

# See if the IBM conversion module is available
try:
    import um_ppibm
    PPIBM_AVAILABLE = True
except ImportError as err:
    PPIBM_AVAILABLE = False


def convpp(fields, output_file, um_file, ibm_format=False,
           keep_addressing=False):
    """
    Convert to PP

    """
    # The original convpp appeared to strip off any leading lbpack digits
    # leaving only the "N1" digit (which can only actually be 1 or 0, but
    # this is caught later in the actual writing routines)
    for field in fields:
        field.lbpack = field.lbpack % 10
        # 32-bit truncated data in a UM file is "unpacked" data in a pp file
        if field.lbpack == 2:
            field.lbpack = 0

    if ibm_format:
        if not PPIBM_AVAILABLE:
            msg = ("Cannot convert to IBM format, um_ppibm module "
                   "not found")
            raise ValueError(msg)
        um_ppibm.fields_to_pp_file_ibm32(
            output_file, fields, umfile=um_file,
            keep_addressing=keep_addressing)
    else:
        mule.pp.fields_to_pp_file(
            output_file, fields, umfile=um_file,
            keep_addressing=keep_addressing)


def _main():
    """
    Main function

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] [options] input_file output_file

    This script will convert a FieldsFile to a PP file.

    Note: IBM number format options require that the optional
          um_ppibm module has been built
    """
    title = _banner(
        "CONVPP-II - Convertor to PP format, version II "
        "(using the Mule API)", banner_char="=")

    # Setup the parser
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter)

    # No need to output help text for the two input files (these are obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)
    parser.add_argument("output_file", help=argparse.SUPPRESS)

    parser.add_argument(
        '--ibm_format', "-I", action='store_true',
        help="convert data written to IBM number format\n")
    parser.add_argument(
        '--keep_addressing', "-k", action='store_true',
        help="Don't modify address elements LBNREC, LBEGIN and LBUSER(2)\n"
             "(might be required for legacy compatability)")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(CONVPP-II) Module Information")),
    report_modules()
    print("")

    input_file = args.input_file

    if mule.pp.file_is_pp_file(input_file):
        raise ValueError("Input file should be a UM File, not a PP file")

    um_file = mule.load_umfile(input_file)

    if um_file.fixed_length_header.dataset_type not in (1, 2, 3, 4):
        msg = (
            "Invalid dataset type ({0}) for file: {1}\nConvpp is only "
            "compatible with FieldsFiles (3), Dumps (1|2) and Ancils (4)"
            .format(um_file.fixed_length_header.dataset_type, input_file))
        raise ValueError(msg)

    # Call the main program to convert the fields for output
    convpp(um_file.fields, args.output_file,
           um_file, ibm_format=args.ibm_format,
           keep_addressing=args.keep_addressing)


if __name__ == "__main__":
    _main()
