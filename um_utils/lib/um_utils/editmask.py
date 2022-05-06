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
EDITMASK is a utility to assist in manual editing of Land Sea Masks in
UM files.  Rather than providing a GUI or direct editing capability
it converts the data into an image file for external editing, and then
allows the result to be placed back into a UM ancil.

"""
import sys
import os
import mule
import numpy as np
import argparse
import textwrap
import warnings
from PIL import Image

from um_utils.version import report_modules
from um_utils.pumf import pprint, PRINT_SETTINGS

# Set pumf's pprinter to only print headers as we don't care
# about the max/min of the field
PRINT_SETTINGS["headers_only"] = True

# Suppress the warning about the file version in ancil files
# as the STASHmaster isn't needed or relevant for this utility
warnings.filterwarnings(
    "ignore",
    r".*Ancillary files do not define the UM version number.*")


def _banner(message, banner_char="%"):
    """A simple function which returns a banner string."""
    return "{0:s}\n* {1:s} *\n{0:s}\n".format(
        banner_char*(len(message)+4), message)


def genimage(ancil_file, image_file):
    """
    Generate a PNG image of the land sea mask found in
    the given file, ready for editing with an external
    program of the user's choice.

    """
    # Find the land sea mask in the file
    anc = mule.AncilFile.from_file(ancil_file)
    lsm_data = None
    for field in anc.fields:
        if field.lbuser4 == 30:
            lsm_data = field.get_data()
            break
    if lsm_data is None:
        raise ValueError("No Land/Sea mask found in file")

    # Scale the 0.0 - 1.0 data to run from 0.0 to 255.0
    lsm_data = lsm_data*255.0

    # Convert to an image, flip the array so that it appears
    # oriented properly north-south as on typical maps etc
    img = Image.fromarray(lsm_data[::-1, :].astype(np.uint8))

    # And output as a PNG file (add the extension if the user
    # didn't to begin with)
    if not image_file.endswith(".png"):
        image_file += ".png"
    img.save(image_file)


def genancil(ancil_file, mask_file, output_file, text_file):
    """
    Generate a copy of the original ancil file using the mask
    data from either an edited image, or a text file produced
    by an earlier run of this method

    """
    # Load the ancillary file we are going to use and find the
    # land sea mask in it
    anc = mule.AncilFile.from_file(ancil_file)
    lsm_field = None
    for field in anc.fields:
        if field.lbuser4 == 30:
            lsm_field = field
            break
    if lsm_field is None:
        raise ValueError("No Land/Sea mask found in file")

    # Get the existing field data
    field_data = field.get_data()

    # The mask file could be an image or a text file
    if mask_file.endswith(".png"):
        # Open the image file, and convert the data inside into
        # an array that will fit back into the field (it has to
        # be flipped from its visual orientation)
        img = Image.open(mask_file)
        lsm_data = (np.array(img)[::-1, :] / 255).astype(">i8")
    elif mask_file.endswith(".txt"):
        lsm_data = field_data.copy()
        # Read the mask file
        with open(mask_file, "r") as mask:
            for line in mask.readlines():
                line = line.strip()
                # Skip comments/blanks
                if line.startswith("#") or line == "":
                    continue
                # If the line is one of the lookup headers
                # at the top of the file, check it against
                # the lookup of the ancil field
                if line.startswith("("):
                    _, lookup, _, text_value = line.split()
                    ancil_value = str(getattr(lsm_field, lookup))
                    if ancil_value != text_value:
                        msg = ("Lookup headers don't agree.\n"
                               "  Text file : {0} = {1}\n"
                               "  Ancil file: {0} = {2}").format(
                                   lookup, text_value, ancil_value
                               )
                        warnings.warn_explicit(msg)
                    continue
                x, y, diff = map(int, line.strip().split())
                lsm_data[x, y] = lsm_data[x, y] - diff
    else:
        raise ValueError(
            "Modification data should be either an image or \n"
            "a text file")

    # Check to make sure this array will fit into the field
    # (it should do provided the user has provided the same
    # file as they used to generate the image)
    if lsm_data.shape != field_data.shape:
        raise ValueError(
            "Image Land/Sea mask is not the same shape as "
            "the mask found in the file")

    # If requested, write the difference file to a text file
    if text_file is not None:
        # Calculate the difference between the two fields
        diff_data = field_data - lsm_data

        # Write the points which have changed to a file
        if not text_file.endswith(".txt"):
            text_file += ".txt"
        with open(text_file, "w") as text:
            text.write(
                "# EDIT MASK: This file can be used to provide \n"
                "# the tool with a listing of which points to change. \n\n"
                "# Lookup headers of lsm field: \n")
            pprint(lsm_field, text)
            text.write(
                "# Changed points; Pairs of X + Y indices, \n"
                "# plus indicator of the type of change: \n"
                "#     1 == Previously land, now sea \n"
                "#    -1 == Previously sea, now land \n")

            for points in zip(*np.where(diff_data != 0.0)):
                text.write("  {0}  {1}  {2}\n".format(points[0],
                                                      points[1],
                                                      diff_data[points]))

    # Populate the field using the data
    provider = mule.ArrayDataProvider(lsm_data)
    lsm_field.set_data_provider(provider)

    # And finall write out the finished file
    anc.to_file(output_file)


def _main():
    """
    Main function; accepts command line arguments.

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] {genimage,genancil} [options]

    Description
    """
    title = _banner(
        "EDIT MASK - Editor for Land Sea Masks in UM Files "
        "(using the Mule API)", banner_char="=")

    # Setup the parser
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,
        )

    # The command has multiple forms depending on what the user is doing
    subparsers = parser.add_subparsers(dest='command')

    # Options for generating image file for editing
    sub_prolog = """    usage:
      {0} genimage [-h] ancil_file image_file

    This will generate an image file which represents the contents
    of the mask from the input file (ready for editing)
               """.format(os.path.basename(sys.argv[0]))

    parser_image = subparsers.add_parser(
        "genimage", formatter_class=argparse.RawTextHelpFormatter,
        description=title + textwrap.dedent(sub_prolog),
        usage=argparse.SUPPRESS,
        help="generate image file (run \"%(prog)s genimage --help\" \n"
        "for specific help on this command)\n ")

    parser_image.add_argument(
        "ancil_file",
        help="UM Ancillary File containing source mask\n ")
    parser_image.add_argument(
        "image_file",
        help="Filename for output image (.png will be appended)\n ")

    # Options for generating new mask file from image
    sub_prolog = """    usage:
      {0} genancil [-h]
               [--text-file text_file] ancil_file mask_file output_file

    This will create a copy of the original file but with the data
    from the mask image inserted into the mask field
               """.format(os.path.basename(sys.argv[0]))

    parser_ancil = subparsers.add_parser(
        "genancil", formatter_class=argparse.RawTextHelpFormatter,
        description=title + textwrap.dedent(sub_prolog),
        usage=argparse.SUPPRESS,
        help="generate ancil file (run \"%(prog)s genancil --help\" \n"
        "for specific help on this command)\n")

    parser_ancil.add_argument(
        "--text-file",
        help="Filename for text file which will contain a list \n"
             "of the changed points, and can be used as the \n"
             "'mask_file' argument in future calls if needed\n",
        required=False, action="store")

    parser_ancil.add_argument(
        "ancil_file",
        help="UM Ancillary File containing original mask\n ")
    parser_ancil.add_argument(
        "mask_file",
        help="Filename of edited mask, either: \n"
             "    A png image produced by 'genimage' \n"
             "    and edited externally\n "
             "OR \n"
             "    A txt file produced by a previous \n"
             "    invocation of 'genancil' (see text_file)\n")
    parser_ancil.add_argument(
        "output_file",
        help="Filename for Ancillary File with new mask data\n")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(EDIT-MASK) Module Information")),
    report_modules()

    if args.command == "genimage":
        genimage(args.ancil_file, args.image_file)
    elif args.command == "genancil":
        genancil(args.ancil_file, args.mask_file,
                 args.output_file, args.text_file)


if __name__ == "__main__":
    _main()
