# (C) Crown Copyright 2016, Met Office. All rights reserved.
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
CUTOUT is a utility for extracting sub-regions from UM fields-files.

Usage:

 * Extract a 20x30 region from a file, starting from the point (5,10)

    >>> ff_new = cutout.cutout(ff, 5, 10, 20, 30)

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


class CutoutDataOperator(mule.DataOperator):
    """
    Operator which extracts a new field representing a sub-region
    of an existing :class:`mule.Field`.

    """
    def __init__(self, zx, zy, nx, ny):
        """
        Setup the operator.

        Args:
            * zx:
                Index of first x point to extract.
            * zy:
                Index of firsy y point to extract.
            * nx:
                Number of x points to extract.
            * ny:
                Number of y points to extract.

        .. Note::
            The point-indices are always referring to the points
            of the P grid - there is no need to try and manually
            adjust the values passed here for non-P grid fields,
            as this operator will calculate the differences itself.

        """
        self.zx = zx
        self.zy = zy
        self.nx = nx
        self.ny = ny

    def new_field(self, field):
        """
        Create and return the new cutout field.

        The returned field will have its grid definition lookup headers
        updated to reflect the target sub-region.

        Args:
            * field:
                The :class:`mule.Field` object containing the source.

        """
        new_field = field.copy()

        new_field.bzx = field.bzx + ((self.zx - 1)*field.bdx)
        new_field.bzy = field.bzy + ((self.zy - 1)*field.bdy)

        # Don't adjust the number of rows or columns in the header if the
        # field was land/sea packed (they should be zero and should remain
        # zero after the cutout)
        if not hasattr(field._data_provider, "_LAND"):
            new_field.lbnpt = self.nx
            new_field.lbrow = self.ny

        new_field.lbhem = 3

        return new_field

    def transform(self, source_field, result_field):
        """Extract the sub-region data from the original field data."""
        # Get the existing data
        data = source_field.get_data()

        # Create a new data array with the desired output sizes
        cut_data = np.empty((self.ny, self.nx))

        # If the requested number of points extend beyond the edge
        # of the domain assume the domain is wrapping and handle it
        # by extracting a section of the array from either side of
        # the dividing edge
        if self.zx + self.nx > source_field.lbnpt and source_field.lbnpt != 0:
            # The left-most part of the target array is filled using
            # values from right-most part of the source array
            cut_data[:, :source_field.lbnpt - self.zx + 1] = (
                data[self.zy-1:self.zy - 1 + self.ny,
                     self.zx - 1:])
            # And the remainder of the target array is filled using
            # values from the left-most part of the source array
            cut_data[:, source_field.lbnpt - self.zx + 1:] = (
                data[self.zy-1:self.zy-1+self.ny,
                     :self.nx + self.zx - source_field.lbnpt - 1])
        else:
            # If the domain is contained entirely within the domain
            # it can be extracted directly
            cut_data[:, :] = data[self.zy-1:self.zy-1+self.ny,
                                  self.zx-1:self.zx-1+self.nx]
        return cut_data


def cutout(ff_src, x_start, y_start, x_points, y_points,
           stashmaster=None):
    """
    Cutout a sub-region from a :class:`mule.FieldsFile` object.

    Args:
        * ff_src:
            The input :class:`mule.FieldsFile` object.
        * x_start:
            The x index at the start of the sub-region.
        * y_start:
            The y index at the start of the sub-region.
        * x_points:
            The number of points to extract in the x direction.
        * y_points:
            The number of points to extract in the y direction.

    Kwargs:
        * stashmaster:
            May be the complete path to a valid STASHmaster
            file, or just the UM version number e.g. "10.2"
            (assuming a UM install exists).  If omitted
            cutout will try to take the version number from
            the headers in the input file.

    .. Warning::
        The input :class:`mule.FieldsFile` must be on a fixed
        resolution grid (see the TRIM utility for working with a
        variable grid)

    """

    def check_regular_grid(dx, dy, fail_context, mdi=0.0):
        # Raise error if dx or dy values indicate an 'irregular' grid.
        invalid_values = [0.0, mdi]
        if dx in invalid_values or dy in invalid_values:
            msg = "Source grid in {0} is not regular."
            raise ValueError(msg.format(fail_context))

    # Determine the grid staggering
    stagger = {3: "new_dynamics", 6: "endgame"}
    if ff_src.fixed_length_header.grid_staggering not in stagger:
        msg = "Grid staggering {0} not supported"
        raise ValueError(msg.format(
            ff_src.fixed_length_header.grid_staggering))
    stagger = stagger[ff_src.fixed_length_header.grid_staggering]

    # Remove empty fields before processing
    ff_src.remove_empty_lookups()

    # Retrieve the stashmaster from the file if one wasn't provided
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

    # Cutout *cannot* continue without the STASHmaster
    if stashm is None:
        msg = "Cannot cutout from file without a valid STASHmaster"
        raise ValueError(msg)

    # Grid-spacing in degrees, ensure this is a regular grid
    rmdi = ff_src.real_constants.real_mdi
    dx = ff_src.real_constants.col_spacing
    dy = ff_src.real_constants.row_spacing
    check_regular_grid(dx, dy, fail_context='header', mdi=rmdi)

    # Want to extract the co-ords of the first P point in the file
    if stagger == "new_dynamics":
        # For ND grids this is given directly
        zy0 = ff_src.real_constants.start_lat
        zx0 = ff_src.real_constants.start_lon
    elif stagger == "endgame":
        # For EG grids the P grid is offset by half a grid spacing
        zy0 = ff_src.real_constants.start_lat + 0.5*dy
        zx0 = ff_src.real_constants.start_lon + 0.5*dx

    # Number of points making up the (P) grid
    nx0 = ff_src.integer_constants.num_cols
    ny0 = ff_src.integer_constants.num_rows

    # Ensure the requested points fit within the target domain (it is allowed
    # to exceed the domain in the X direction provided the domain wraps)
    horiz_grid = ff_src.fixed_length_header.horiz_grid_type
    msg = ("The given cutout parameters extend outside the dimensions of the "
           "grid contained in the source file.")
    if y_start + y_points > ny0 or (x_start + x_points > nx0
                                    and horiz_grid % 10 == 3):
        raise ValueError(msg)

    # Create a new fieldsfile to store the cutout fields
    ff_dest = ff_src.copy()

    # Calculate new file headers describing the cutout domain
    if stagger == "new_dynamics":
        # For ND grids this is given directly
        ff_dest.real_constants.start_lat = zy0 + (y_start - 1)*dy
        ff_dest.real_constants.start_lon = zx0 + (x_start - 1)*dx
    elif stagger == "endgame":
        # For EG grids the header values are offset by half a grid spacing
        ff_dest.real_constants.start_lat = zy0 + ((y_start - 1.5) * dy)
        ff_dest.real_constants.start_lon = zx0 + ((x_start - 1.5) * dx)

    # The new grid type will be a LAM, and its size is whatever the size of
    # the specified cutout domain is going to be
    ff_dest.fixed_length_header.horiz_grid_type = 3
    ff_dest.integer_constants.num_cols = x_points
    ff_dest.integer_constants.num_rows = y_points

    # Ready to begin processing of each field
    for i_field, field_src in enumerate(ff_src.fields):

        # Ensure this field is on a regular grid
        check_regular_grid(field_src.bdx, field_src.bdy,
                           fail_context='field#{0:d}'.format(i_field),
                           mdi=field_src.bmdi)

        # In case the field has extra data, abort
        if field_src.lbext != 0:
            msg = ('field#{0} has extra data, which cutout '
                   'does not support')
            raise ValueError(msg.format(i_field))

        # If the grid is not a regular lat-lon grid, abort
        if field_src.lbcode % 10 != 1:
            msg = ('field#{0} is not on a regular lat/lon grid')
            raise ValueError(msg.format(i_field))

        # Retrieve the grid-type for this field from the STASHmaster and
        # use it to adjust the indices to extract for the non-P grids
        if field_src.lbuser4 in stashm:
            grid_type = stashm[field_src.lbuser4].grid
        else:
            msg = "STASH code ({0}) not found in STASHmaster: {1}"
            raise ValueError(msg.format(field_src.lbuser4, stashm.filename))

        if grid_type == 19:  # V Points
            if stagger == "new_dynamics":
                # One less row than the P grid
                cut_y = y_points - 1
                cut_x = x_points
            elif stagger == "endgame":
                # One more row than the P grid
                cut_y = y_points + 1
                cut_x = x_points
        elif grid_type == 18:  # U Points
            if stagger == "new_dynamics":
                # Same as the P grid
                cut_y = y_points
                cut_x = x_points
            elif stagger == "endgame":
                # Same as the P grid
                cut_y = y_points
                cut_x = x_points
        elif grid_type == 11:  # UV Points
            if stagger == "new_dynamics":
                # One less row than the P grid
                cut_y = y_points - 1
                cut_x = x_points
            elif stagger == "endgame":
                # One more row than the P grid
                cut_y = y_points + 1
                cut_x = x_points
        elif grid_type in [1, 2, 3, 21]:  # P Points (or land packed points)
            # Are already correct as defined above
            cut_y = y_points
            cut_x = x_points
        else:
            msg = ('Field {0} has unsupported grid type {1} '
                   'and will not be included in the output')
            warnings.warn(msg.format(i_field, grid_type))
            continue

        # Can now construct the data operator for the cutout operation and
        # assign it to the field
        cutout_operator = CutoutDataOperator(x_start, y_start, cut_x, cut_y)
        field = cutout_operator(field_src)

        ff_dest.fields.append(field)

    return ff_dest


def _main():
    """
    Main function; accepts command line arguments and provides the cutout
    specification, input and output files to be cutout.

    """
    # Create a quick version of the regular raw description formatter which
    # adds spaces between the option help text
    class BlankLinesHelpFormatter(argparse.HelpFormatter):
        def _split_lines(self, text, width):
            return super(
                BlankLinesHelpFormatter, self)._split_lines(text, width) + ['']

    parser = argparse.ArgumentParser(
        usage="%(prog)s [options] input_file output_file zx zy nx ny",
        description="""
        CUTOUT-II - Cutout tool for UM Files, version II (using the Mule API).

        This script will extract a sub-region from a UM FieldsFile, producing
        a new file.
        """,
        formatter_class=BlankLinesHelpFormatter,
        )

    # No need to output help text for the files (it's obvious)
    parser.add_argument("input_file", help=argparse.SUPPRESS)
    parser.add_argument("output_file", help=argparse.SUPPRESS)

    parser.add_argument("zx",
                        help="the starting x (column) index of the region "
                        "to cutout from the original file",
                        type=int
                        )
    parser.add_argument("zy",
                        help="the starting y (row) index of the region "
                        "to cutout from the original file",
                        type=int
                        )
    parser.add_argument("nx",
                        help="the number of x (column) points to cutout "
                        "from the original file",
                        type=int,
                        )
    parser.add_argument("ny",
                        help="the number of y (row) points to cutout "
                        "from the original file",
                        type=int,
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

        # Perform the cutout
        ff_out = cutout(ff, args.zx, args.zy, args.nx, args.ny,
                        args.stashmaster)

        # Write the result out to the new file
        ff_out.to_file(args.output_file)

    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)

if __name__ == "__main__":
    _main()
