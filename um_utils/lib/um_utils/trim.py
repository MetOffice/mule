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
TRIM is a utility for extracting fixed-resolution sub-regions from
variable resolution UM fields-files.

Usage:

 * Extract the central region from a typical variable resolution file
   (in which there are 9 fixed-resoltion areas)

    >>> ff_new = trim.trim_fixed_region(ff, 2, 2)

   .. Note::
       This returns a new :class:`mule.FieldsFile` object, its headers
       and lookup headers will reflect the target region, and each
       field object's data provider will be setup to return the data
       for the target region.

"""
import os
import re
import sys
import mule
import mule.pp
import argparse
import textwrap
import numpy as np
from um_utils.stashmaster import STASHmaster
from um_utils.cutout import cutout
from um_utils.version import report_modules
from um_utils.pumf import _banner


def _get_fixed_indices(array, tolerance=1.0e-9):
    """
    Calculate the indices of regions with constant gradient from an array.

    Returns a list of lists with the outer list containing one element
    for each separate fixed resolution section discovered, and the inner
    lists containing the indices of the section in the original array.

    Args:
        * array:
            The 1-dimensional array of values.

    Kwargs:
        * tolerance:
            When examining the 2nd-derivative of the input array this
            tolerance is used to determine where the fixed resolution
            regions begin and end.

    """
    # Get the first derivative of the array
    array_delta = np.gradient(array)

    # Find the indices where the second derivative is above or below the
    # tolerance (i.e. the points of blending in the original array)
    indices_up = np.where(np.gradient(array_delta) > tolerance)
    indices_dn = np.where(np.gradient(array_delta) < -tolerance)

    # Create an index array and remove these points from it (leaving the fixed
    # points.  Note that there can be mutliple blending groups if found above)
    indices = set(range(len(array)))
    for group in indices_up:
        indices -= set(group)
    for group in indices_dn:
        indices -= set(group)
    indices = list(indices)

    # Now find the unique groupings of indices which make up the different
    # fixed regions from the original
    start = indices[0]
    region_indices = []
    for point in range(1, len(indices)):
        # If a discontinuous point is found, save the working region
        if (indices[point] - indices[point - 1]) != 1:
            region_indices.append(indices[start:point])
            # ... and update the start point for the next pass
            start = point
    # At the end of the loop capture the final region
    if start != point:
        region_indices.append(indices[start:])

    # The above will have selected the interior points but the fixed region
    # technically starts one point prior/after this, so expand the regions
    # by 1 point (where possible)
    for iregion in range(len(region_indices)):
        region = region_indices[iregion]
        start, end = [], []
        if region[0] != indices[0]:
            start = [region[0] - 1]
        if region[-1] != indices[-1]:
            end = [region[-1] + 1]
        region_indices[iregion] = start + region + end

    return region_indices


def trim_fixed_region(ff_src, region_x, region_y, stdout=None):
    """
    Extract a fixed resolution sub-region from a variable resolution
    :class:`mule.FieldsFile` object.

    Args:
        * ff_src:
            The input :class:`mule.FieldsFile` object.
        * region_x:
            The x index of the desired sub-region (starting from 1)
        * region_y:
            The y index of the desired sub-region (starting from 1)

    Kwargs:
        * stdout:
            The open file-like object to write informational output to,
            default is to use sys.stdout.

    .. Warning::

        The :class:`mule.FieldsFile` object *must* have an attached set of
        STASHmaster information, or trim cannot operate correctly.

    """
    # Setup printing
    if stdout is None:
        stdout = sys.stdout

    # Check if the field looks like a variable resolution file
    if not (hasattr(ff_src, "row_dependent_constants") and
            hasattr(ff_src, "column_dependent_constants")):
        msg = "Cannot trim fixed resolution file"
        raise ValueError(msg)

    # We are going to use CUTOUT to do the final cutout operation, but
    # in order to have it extract the correct points we must first create
    # a modified version of the original input object.  To avoid making
    # any changes to the user's input object, take a copy of it here
    ff = ff_src.copy(include_fields=True)

    # We need the arrays giving the latitudes and longitudes of the P grid
    # (note the phi_p array has an extra missing point at the end)
    phi_p = ff.row_dependent_constants.phi_p[:-1]
    lambda_p = ff.column_dependent_constants.lambda_p

    # The first step here is to extract the indices of the regions which
    # have fixed grid spacings
    phi_p_regions = _get_fixed_indices(phi_p)
    lambda_p_regions = _get_fixed_indices(lambda_p)

    num_x_regions = len(lambda_p_regions)
    num_y_regions = len(phi_p_regions)

    stdout.write(_banner("Locating fixed regions") + "\n")

    # Double check the requested region actually exists in the results
    if num_x_regions < region_x or region_x <= 0:
        msg = "Region {0},{1} not found (1 - {2} regions in the X-direction)"
        raise ValueError(msg.format(region_x, region_y, num_x_regions))

    if num_y_regions < region_y or region_y <= 0:
        msg = "Region {0},{1} not found (1 - {2} regions in the Y-direction)"
        raise ValueError(msg.format(region_x, region_y, num_y_regions))

    # We need to know the grid staggering for the next part
    stagger = {3: "new_dynamics", 6: "endgame"}
    stagger = stagger[ff.fixed_length_header.grid_staggering]

    # Extend the eastern edge of each region by one on ENDGame; the reason for
    # this is that all EG grids do not end on a U column - therefore the
    # region where all grids are within the fixed part of the grid includes
    # eastern-most P point (except for regions sharing their eastern column
    # with the edge of the original domain)
    if stagger == "endgame":
        for i_region, region in enumerate(lambda_p_regions):
            eastern_edge = region[-1]
            if eastern_edge < len(lambda_p) - 1:
                region.extend([eastern_edge + 1])

    stdout.write("X-regions:")
    for i_region, region in enumerate(lambda_p_regions):
        stdout.write(
            "\n  {0}: from {1} to {2} ({3} points)"
            .format(i_region + 1, region[0] + 1, region[-1] + 1, len(region)))
        if i_region + 1 == region_x:
            stdout.write(" (selected)")

    stdout.write("\n\nY-regions:")
    for i_region, region in enumerate(phi_p_regions):
        stdout.write(
            "\n  {0}: from {1} to {2} ({3} points)"
            .format(i_region + 1, region[0] + 1, region[-1] + 1, len(region)))
        if i_region + 1 == region_y:
            stdout.write(" (selected)")
    stdout.write("\n\n")

    # The start and size arguments which will need to be passed to cutout
    # can now be picked out of the selected array
    x_start = lambda_p_regions[region_x - 1][0]
    x_size = len(lambda_p_regions[region_x - 1])
    y_start = phi_p_regions[region_y - 1][0]
    y_size = len(phi_p_regions[region_y - 1])

    # Before we can call cutout, we need to make this object *look like* a
    # fixed resolution file.  This is because cutout is designed to update
    # the headers describing the grid, and these are unset for a variable
    # file.  We will set them so that the file looks like the entire grid
    # is defined at the fixed resolution of the region to be extracted.

    # Calculate the grid spacing of the selected regions - this is just the
    # difference between the first two points in each direction
    new_dx = lambda_p[x_start + 1] - lambda_p[x_start]
    new_dy = phi_p[y_start + 1] - phi_p[y_start]
    ff.real_constants.row_spacing = new_dy
    ff.real_constants.col_spacing = new_dx

    # Check that the file has a STASHmaster attached to it
    # Trim *cannot* continue without the STASHmaster
    if ff.stashmaster is None:
        msg = "Cannot trim regions from a file without a valid STASHmaster"
        raise ValueError(msg)

    # For the origin, take the lat/lon values at the start of the selected
    # region and back-trace to what the first P point would have been if the
    # entire grid were at the fixed resolution calculated above
    new_zx = lambda_p[x_start] - new_dx * x_start
    new_zy = phi_p[y_start] - new_dy * y_start
    p_zx = new_zx
    p_zy = new_zy
    if stagger == "endgame":
        # For EG grids the origin is an additional half grid spacing
        # behind the P origin (calculated above)
        new_zx = new_zx - 0.5 * new_dx
        new_zy = new_zy - 0.5 * new_dy

    if (stagger == "new_dynamics" or (stagger == "endgame" and
         ff.fixed_length_header.dataset_type == 4)):
        # In all ND files and EG ancils the real constants match P origin
        ff.real_constants.start_lon = p_zx
        ff.real_constants.start_lat = p_zy
    elif stagger == "endgame":
        ff.real_constants.start_lon = new_zx
        ff.real_constants.start_lat = new_zy

    # Fixed files don't have row/column dependent constants, so discard them
    ff.row_dependent_constants = None
    ff.column_dependent_constants = None

    # Now we must repeat these steps for each of the field objects
    for field in ff.fields:
        # Skip fields which won't have the required headers
        if field.lbrel not in (2, 3):
            continue

        # The grid spacing is just the same as in the file header
        field.bdx = new_dx
        field.bdy = new_dy

        # The origin point depends on the staggering and the type of field
        if field.stash is not None:
            grid_type = field.stash.grid
        else:
            # Skip this field (it won't be output by cutout in the end anyway)
            continue

        if grid_type == 19:  # V Points
            if stagger == "new_dynamics":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - 0.5 * new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - 0.5 * new_dx
                field.bzy = new_zy - new_dy
        elif grid_type == 18:  # U Points
            if stagger == "new_dynamics":
                field.bzx = new_zx - 0.5 * new_dx
                field.bzy = new_zy - new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - 0.5 * new_dy
        elif grid_type == 11:  # UV Points
            if stagger == "new_dynamics":
                field.bzx = new_zx - 0.5 * new_dx
                field.bzy = new_zy - 0.5 * new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - new_dy
        elif grid_type in [1, 2, 3, 21]:  # P points
            if stagger == "new_dynamics":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - 0.5 * new_dx
                field.bzy = new_zy - 0.5 * new_dy

    # Should now be able to hand things off to cutout - note that since
    # normally cutout expects the start indices to be 1-based we have to adjust
    # the inputs slightly here to end up with the correct output
    ff_out = cutout(ff, x_start + 1, y_start + 1, x_size, y_size, stdout)

    return ff_out


def _main():
    """
    Main function; accepts command line arguments and provides the fixed
    region specification, input and output files.

    """
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] [options] input_file output_file region_x region_y

    This script will extract a fixed-grid sub-region from a variable
    resolution UM FieldsFile, producing a new file.
    """
    title = _banner(
        "TRIM - Fixed region extraction tool for UM Files "
        "(using the Mule API)",
        banner_char="=")

    # Setup the parser
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,)

    # No need to output help text for the files (it's obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)
    parser.add_argument("output_file", help=argparse.SUPPRESS)

    parser.add_argument(
        "region_x", type=int,
        help="the x index of the *region* to extract, starting from 1. \n"
        "In a typical variable resolution FieldsFile the central region \n"
        "will be given by '2'\n ")

    parser.add_argument(
        "region_y", type=int,
        help="the y index of the *region* to extract, starting from 1. \n"
        "In a typical variable resolution FieldsFile the central region \n"
        "will be given by '2'\n")

    parser.add_argument(
        "--stashmaster",
        help="either the full path to a valid stashmaster file, or a UM \n"
        "version number e.g. '10.2'; if given a number trim will look in \n"
        "the path defined by: \n"
        "  mule.stashmaster.STASHMASTER_PATH_PATTERN \n"
        "which by default is: \n"
        "  $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A\n")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(TRIM) Module Information")),
    report_modules()
    print("")

    filename = args.input_file
    if os.path.exists(filename):
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

        # Abort for pp files (they don't have the required information)
        if mule.pp.file_is_pp_file(filename):
            msg = "File {0} is a pp file, which trim does not support"
            raise ValueError(msg.format(filename))

        # Load the file using Mule - filter it according to the file types
        # which cutout can handle
        ff = mule.load_umfile(filename, stashmaster=stashm)
        if ff.fixed_length_header.dataset_type not in (1, 2, 3, 4):
            msg = (
                "Invalid dataset type ({0}) for file: {1}\nTrim is only "
                "compatible with FieldsFiles (3), Dumps (1|2) and Ancils (4)"
                .format(ff.fixed_length_header.dataset_type, filename))
            raise ValueError(msg)

        # Perform the trim operation
        ff_out = trim_fixed_region(ff, args.region_x, args.region_y)

        # Write the result out to the new file
        ff_out.to_file(args.output_file)

    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)


if __name__ == "__main__":
    _main()
