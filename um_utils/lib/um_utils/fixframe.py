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
Fixframe is a utility to convert a MakeBC frame file to a
CreateBC compatible frame file.

The file headers in a MakeBC frame file contain the grid information
of the original fields rather than the cutout frame fields.

Fixframe will create a new :class:`mule.FieldsFile` object that uses
the grid information from the frame fields to update the file headers.

Usage:

 * Take a :class:`mule.FieldsFile` object and return a :class:`mule.FieldsFile`
   object that is compatible with CreateBC.

   >>> fieldsfile_object = fixframe.fixframe(umfile_object)

"""
import os
import sys
import mule
import mule.pp
import argparse
import textwrap
from um_utils.version import report_modules
from um_utils.pumf import _banner


def fixframe(origfile):
    """
    Given a MakeBC frame file as a UMFile or FieldsFile object
    return a FieldsFile object which is compatible with CreateBC.

    Args:
        * origfile:
            A :class:`mule.FieldsFile` object.

    """
    # Copy the original file in its entirety
    fixedfile = origfile.copy(include_fields=True)

    # Check that file has orography, which should always be the first field
    # in a MakeBC frame
    orog_field = fixedfile.fields[0]
    if (orog_field.lbrel not in (2, 3)):
        msg = "First field in file has unrecognised release number {0}"
        raise ValueError(msg.format(orog_field.lbrel))
    if (orog_field.lbuser4 != 33):
        msg = ("First field in file has stashcode {0} but expected orography "
               "(stashcode 33) for a MakeBC frame file")
        raise ValueError(msg.format(orog_field.lbuser4))

    # Copy the rows and row_length from field header to file header
    fixedfile.integer_constants.num_rows = orog_field.lbrow
    fixedfile.integer_constants.num_cols = orog_field.lbnpt

    # Copy the start lat and start long. Convert from zeroth P point
    # to start lat/long (origin) of grid
    if fixedfile.fixed_length_header.grid_staggering == 6:
        # ENDGame - Add half grid spacing
        stagger_factor = 0.5
    else:
        # New Dynamics - Add single grid spacing
        stagger_factor = 1
    fixedfile.real_constants.start_lat = orog_field.bzy + \
        (stagger_factor * orog_field.bdy)
    fixedfile.real_constants.start_lon = orog_field.bzx + \
        (stagger_factor * orog_field.bdx)

    # Set hemisphere indicator/grid type
    if orog_field.lbcode == 1:  # Regular lat/lon
        fixedfile.fixed_length_header.horiz_grid_type = orog_field.lbhem
    elif orog_field.lbcode == 101:  # Rotated regular lat/lon
        fixedfile.fixed_length_header.horiz_grid_type = orog_field.lbhem + \
            100
    else:
        msg = ("LBCODE = {0} indicates that frame file is not on a "
               "regular lat/lon grid.")
        raise ValueError(msg.format(orog_field.lbcode))

    # Frames files have lblrec set incorrectly for WGDOS packed fields
    # (using 32 bit words when it should be 64 bit)
    for field in fixedfile.fields:
        if field.lbpack % 10 == 1:
            # Convert from num 32 to 64 bit words
            field.lblrec = (field.lblrec + 1)/2

    return fixedfile


def _printgrid(umfile, filename, stdout=None):
    """
    Print grid information to stdout

    """
    # Setup output
    if stdout is None:
        stdout = sys.stdout

    msg = ("\n Grid information for file: {0}\n\n"
           " Latitude of first row     : {1:12}\n"
           " Longitude of first column : {2:12}\n"
           " Number of rows            : {3:12}\n"
           " Number of columns         : {4:12}\n")
    stdout.write(msg.format(filename, umfile.real_constants.raw[3],
                            umfile.real_constants.raw[4],
                            umfile.integer_constants.raw[7],
                            umfile.integer_constants.raw[6]))


def _main():
    """
    Main function; accepts command line argument for paths to
    the input and output files.

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] input_filename output_filename

    This script will take a MakeBC generated frame file and produce
    a CreateBC compatible frame file.
    """
    title = _banner(
        "FIXFRAME - Converter for old-style UM frames files "
        "(Using the Mule API)", banner_char="=")

    # Setup the parser
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,
        )

    parser.add_argument(
        "input_filename",
        help="First argument is the path and name of the MakeBC frames file \n"
        "to be fixed\n ")
    parser.add_argument(
        "output_filename",
        help="Second argument is the path and name of the CreateBC frames \n"
        "file to be produced\n")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(fixframe) Module Information")),
    report_modules()
    print("")

    input_filename = args.input_filename
    if not os.path.exists(input_filename):
        msg = "File not found: {0}".format(input_filename)
        raise ValueError(msg)

    # Abort for pp files (they don't have the required information)
    if mule.pp.file_is_pp_file(input_filename):
        msg = "File {0} is a pp file, which fixframe does not support"
        raise ValueError(msg.format(input_filename))

    output_filename = args.output_filename

    # Read in file as a FieldsFile - MakeBC frames do not pass fieldsfile
    # validation so will generate some warnings
    origfile = mule.FieldsFile.from_file(input_filename)
    _printgrid(origfile, input_filename)
    # Fix the headers
    fixedfile = fixframe(origfile)
    _printgrid(fixedfile, output_filename)
    # Write file
    fixedfile.to_file(output_filename)


if __name__ == "__main__":
    _main()
