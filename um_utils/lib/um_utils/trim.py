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
import mule
import argparse
import warnings
import numpy as np
from um_utils.stashmaster import STASHmaster
from um_utils.cutout import cutout


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


def trim_fixed_region(ff_src, region_x, region_y, stashmaster=None):
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
        * stashmaster:
            May be the complete path to a valid STASHmaster
            file, or just the UM version number e.g. "10.2"
            (assuming a UM install exists).  If omitted
            cutout will try to take the version number from
            the headers in the input file.

    """

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

    # Double check the requested region actually exists in the results
    if len(lambda_p_regions) < region_x:
        msg = "Region {0}{1} not found (only {2} regions in the X-direction)"
        raise ValueError(msg.format(region_x, region_y, len(lambda_p_regions)))

    if len(phi_p_regions) < region_y:
        msg = "Region {0},{1} not found (only {2} regions in the Y-direction)"
        raise ValueError(msg.format(region_x, region_y, len(phi_p_regions)))

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

    # We need to know the grid staggering for the next part
    stagger = {3: "new_dynamics", 6: "endgame"}
    stagger = stagger[ff.fixed_length_header.grid_staggering]

    # Setup the STASHmaster; if the user didn't supply an override
    # try to take the version from the file:
    if stashmaster is None:
        # If the user hasn't set anything, load the STASHmaster for the
        # version of the UM defined in the first file
        stashm = STASHmaster.from_umfile(ff_src)
    else:
        # If the settings looks like a version number, try to load the
        # STASHmaster from that version, otherwise assume it is the path
        if re.match(r"\d+.\d+", stashmaster):
            stashm = STASHmaster.from_version(stashmaster)
        else:
            stashm = STASHmaster.from_file(stashmaster)

    # Trim *cannot* continue without the STASHmaster
    if stashm is None:
        msg = "Cannot trim regions from a file without a valid STASHmaster"
        raise ValueError(msg)

    # For the origin, take the lat/lon values at the start of the selected
    # region and back-trace to what the first P point would have been if the
    # entire grid were at the fixed resolution calculated above
    new_zx = lambda_p[x_start] - new_dx*(x_start + 1)
    new_zy = phi_p[y_start] - new_dy*(y_start + 1)
    if stagger == "endgame":
        # For EG grids the origin is an additional half grid spacing
        # behind the P origin (calculated above)
        new_zx = new_zx - 0.5*new_dx
        new_zy = new_zy - 0.5*new_dy
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
        if field.lbuser4 in stashm:
            grid_type = stashm[field.lbuser4].grid
        else:
            msg = "STASH code ({0}) not found in STASHmaster: {1}"
            raise ValueError(msg.format(field_src.lbuser4, stashm.filename))

        if grid_type == 19:  # V Points
            if stagger == "new_dynamics":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - 0.5*new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - 0.5*new_dx
                field.bzy = new_zy - new_dy
        elif grid_type == 18:  # U Points
            if stagger == "new_dynamics":
                field.bzx = new_zx - 0.5*new_dx
                field.bzy = new_zy - new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - 0.5*new_dy
        elif grid_type == 11:  # UV Points
            if stagger == "new_dynamics":
                field.bzx = new_zx - 0.5*new_dx
                field.bzy = new_zy - 0.5*new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - new_dy
        elif grid_type in [1, 2, 3, 21]:  # P points
            if stagger == "new_dynamics":
                field.bzx = new_zx - new_dx
                field.bzy = new_zy - new_dy
            elif stagger == "endgame":
                field.bzx = new_zx - 0.5*new_dx
                field.bzy = new_zy - 0.5*new_dy

    # Should now be able to hand things off to cutout - note that since
    # normally cutout expects the start indices to be 1-based we have to adjust
    # the inputs slightly here to end up with the correct output
    ff_out = cutout(ff, x_start + 1, y_start + 1, x_size - 1, y_size - 1,
                    stashmaster)

    return ff_out


def _main():
    """
    Main function; accepts command line arguments and provides the fixed
    region specification, input and output files.

    """
    # Create a quick version of the regular raw description formatter which
    # adds spaces between the option help text
    class BlankLinesHelpFormatter(argparse.HelpFormatter):
        def _split_lines(self, text, width):
            return super(
                BlankLinesHelpFormatter, self)._split_lines(text, width) + ['']

    parser = argparse.ArgumentParser(
        usage="%(prog)s [options] input_file output_file region_x region_y",
        description="""
        TRIM - Fixed region extraction tool for UM Files (using the Mule API).

        This script will extract a fixed-grid sub-region from a variable
        resolution UM FieldsFile, producing a new file.
        """,
        formatter_class=BlankLinesHelpFormatter,
        )

    # No need to output help text for the files (it's obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)
    parser.add_argument("output_file", help=argparse.SUPPRESS)

    parser.add_argument("region_x",
                        help="the x index of the *region* to extract, "
                        "starting from 1.  In a typical variable resolution "
                        "FieldsFile the central region will be given by '2'.",
                        type=int
                        )
    parser.add_argument("region_y",
                        help="the y index of the *region* to extract, "
                        "starting from 1.  In a typical variable resolution "
                        "FieldsFile the central region will be given by '2'.",
                        type=int
                        )
    parser.add_argument("--stashmaster",
                        help="either the full path to a valid stashmaster "
                        "file, or a UM version number e.g. '10.2'; if given "
                        "a number pumf will look in the following path: "
                        "$UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A",
                        )

    args = parser.parse_args()

    filename = args.input_file
    if os.path.exists(filename):
        # Load the file using Mule - note we explicitly load a FieldsFile
        # as we don't expect cutout to work properly on anything else
        ff = mule.FieldsFile.from_file(filename)

        # Perform the trim operation
        ff_out = trim_fixed_region(ff, args.region_x, args.region_y)

        # Write the result out to the new file
        ff_out.to_file(args.output_file)

    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)

if __name__ == "__main__":
    _main()
