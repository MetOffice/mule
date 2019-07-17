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
CUTOUT is a utility for extracting sub-regions from UM fields-files.

A cutout can be performed either by specifying the new region in terms
of indices into the grid of the source file, or by providing a pair of
co-ordinates which specify the SW and NE corners of the desired domain
within the source file.

Usage:

 * Extract a 20x30 region from a file, starting from the point (5,10)

    >>> ff_new = cutout.cutout(ff, 5, 10, 20, 30)

 * Extract the region between (13.0 W 50.0 N) and (5.0 E 60 N)

    >>> ff_new = cutout.cutout_coords(ff, -13.0, 50.0, 5.0, 60.0)

   .. Note::
       This returns a new :class:`mule.FieldsFile` object, its headers
       and lookup headers will reflect the target region, and each
       field object's data provider will be setup to return the data
       for the target region.

   .. Warning::
       Both cutout methods here expect the :class:`mule.FieldsFile`
       object to be on a regular grid - see the alternative
       :mod:`um_utils.trim` module for working with variable resolution
       files.

"""
import os
import re
import sys
import mule
import mule.pp
import argparse
import textwrap
import warnings
import numpy as np
from um_utils.stashmaster import STASHmaster
from um_utils.version import report_modules
from um_utils.pumf import _banner

GRID_STAGGER = {3: "new_dynamics", 6: "endgame"}


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

        # This is now a LAM so update the hemisphere code
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


class CoordRotator(object):
    """A class which assists with performing pole rotations."""

    def __init__(self, pole_lon, pole_lat):
        """
        Initialise the rotator object, providing the pole co-ordinates of
        the desired domain

        Args:
            * pole_lon:
                Longitude of target domain's North pole, in degrees.
            * pole_lat:
                Latitude of target domain's North pole, in degrees.

        """
        # Store the values in degrees for reference only
        self.pole_lon = pole_lon
        self.pole_lat = pole_lat

        # Convert to radians for use in calculations
        self.pole_lon_rads = self.to_rads(pole_lon)
        self.pole_lat_rads = self.to_rads(pole_lat)

        # Calculate the longitudinal angle the grid needs to be rotated
        # by to place its pole on the 180 degree meridian
        if self.pole_lon_rads == 0.0:
            self.to_meridian = 0.0
        else:
            self.to_meridian = self.pole_lon_rads - np.pi

    @staticmethod
    def to_rads(degrees):
        """Simple function to go from degrees to radians"""
        return (degrees % 360.0)*(np.pi/180.0)

    @staticmethod
    def to_degrees(rads):
        """Simple function to go from radians to degrees"""
        return rads*(180.0/np.pi)

    def rotate(self, longitude, latitude):
        """
        Rotate a pair of co-ordinates from a regular lat-lon grid onto
        the rotated grid defined by this object.

        Args:
            * longitude:
                Longitude of the desired point, in degrees
            * latitude:
                Latitude of the desired point, in degrees

        """
        # Convert the input co-ordinates to radians
        lon_rads = self.to_rads(longitude)
        lat_rads = self.to_rads(latitude)

        # Adjust the input longitude in the same manner as would be needed
        # to align the regular pole's 180 degree meridian with the new pole
        lon_temp = (
            np.mod(lon_rads - self.to_meridian + 5*np.pi, 2*np.pi) - np.pi)

        # Can now calculate the new latitude by again applying the same
        # rotation as would be needed to go from one pole to the other
        bpart = np.cos(lon_temp)*np.cos(lat_rads)
        lat_rotated = np.arcsin(-np.cos(self.pole_lat_rads)*bpart +
                                np.sin(self.pole_lat_rads)*np.sin(lat_rads))

        # Knowing the latitude allows the correct longitude to be inferred
        t1 = np.cos(self.pole_lat_rads)*np.sin(lat_rads)
        t2 = np.sin(self.pole_lat_rads)*bpart
        lon_rotated = -np.arccos((t1 + t2)/np.cos(lat_rotated))

        # Correct this based on the original adjustment to meet the meridian
        if lon_temp >= 0.0 and lon_temp <= np.pi:
            lon_rotated = -1.0*lon_rotated

        # ...and convert the values back to degrees
        return self.to_degrees(lon_rotated), self.to_degrees(lat_rotated)

    def unrotate(self, longitude, latitude):
        """
        Rotate a pair of co-ordinates from the grid defined by this object
        onto a regular lat-lon grid.

        Args:
            * longitude:
                Longitude of the desired point, in degrees
            * latitude:
                Latitude of the desired point, in degrees

        """
        # Convert the input co-ordinates to radians
        lon_rads = self.to_rads(longitude)
        lat_rads = self.to_rads(latitude)

        # Reverse the rotation for the latitude
        cpart = np.cos(lon_rads)*np.cos(lat_rads)
        lat_unrotated = np.arcsin(np.cos(self.pole_lat_rads)*cpart +
                                  np.sin(self.pole_lat_rads)*np.sin(lat_rads))

        # Use the unrotated latitude to infer what the longitude would be on
        # the 180 degree meridian of the regular pole
        t1 = -np.cos(self.pole_lat_rads)*np.sin(lat_rads)
        t2 = np.sin(self.pole_lat_rads)*cpart
        lon_unrotated = -np.arccos((t1 + t2)/np.cos(lat_unrotated))

        # Ensure this is in the correct range, then rotate it back into
        # position to get the final longitude
        lon_temp = np.mod((lon_rads + 5*np.pi), 2*np.pi) - np.pi
        if lon_temp >= 0.0 and lon_temp <= np.pi:
            lon_unrotated = -1.0*lon_unrotated
        lon_unrotated += self.to_meridian

        # ...and convert the values back to degrees
        return self.to_degrees(lon_unrotated), self.to_degrees(lat_unrotated)


def cutout_coords(ff_src, sw_lon, sw_lat, ne_lon, ne_lat,
                  native_grid=False, stdout=None):
    """
    Cutout a sub-region from a :class:`mule.FieldsFile` object, based on
    the lat-lon co-ordinates of the region.

    Args:
        * ff_src:
            The input :class:`mule.FieldsFile` object.
        * sw_lon:
            The longitude of the SW corner point of the sub-region.
        * sw_lat:
            The latitude of the SW corner point of the sub-region.
        * ne_lon:
            The longitude of the NE corner point of the sub-region.
        * ne_lat:
            The latitude of the NE corner point of the sub-region.

    Kwargs:
        * native_grid:
            If set to True, assumes that the given co-ordinates are on the
            same grid as the source (otherwise, assumes they are regular
            lat/lon co-ordinates and applies any required rotations).
        * stdout:
            The open file-like object to write informational output to,
            default is to use sys.stdout.

    .. Warning::
        The input :class:`mule.FieldsFile` must be on a fixed
        resolution grid (see the TRIM utility for working with a
        variable grid)

    """
    # Setup printing
    if stdout is None:
        stdout = sys.stdout

    # Get the pole co-ordinates from the file
    pole_lon = ff_src.real_constants.north_pole_lon
    pole_lat = ff_src.real_constants.north_pole_lat

    stdout.write(_banner("Processing co-ordinates")+"\n")

    stdout.write(
        "Requested area ({0:.2f} E {1:.2f} N) to ({2:.2f} E {3:.2f} N)\n"
        .format(sw_lon % 360.0, sw_lat, ne_lon % 360.0, ne_lat))

    # Check to see if it's a rotated grid (unless this has been disabled)
    rotated = False
    if native_grid:
        stdout.write("\nNative grid setting active, will assume given "
                     "co-ordinates are already on the correct grid.\n")
    elif pole_lat != 90.0 or pole_lon != 0.0:
        # If it is translate the co-ordinates onto the grid
        coord_rotator = CoordRotator(pole_lon, pole_lat)

        # Calculate the other (not user provided) corner points
        nw_lon, nw_lat = coord_rotator.rotate(sw_lon, ne_lat)
        se_lon, se_lat = coord_rotator.rotate(ne_lon, sw_lat)

        # As well as the original corner points
        sw_lon, sw_lat = coord_rotator.rotate(sw_lon, sw_lat)
        ne_lon, ne_lat = coord_rotator.rotate(ne_lon, ne_lat)

        # Now, adjust the corners to ensure the domain covers as much
        # of the area as possible
        sw_lon = min([sw_lon, ne_lon, nw_lon, se_lon])
        ne_lon = max([sw_lon, ne_lon, nw_lon, se_lon])
        sw_lat = min([sw_lat, ne_lat, nw_lat, se_lat])
        ne_lat = max([sw_lat, ne_lat, nw_lat, se_lat])

        # Save a flag indicating that a transform was performed (for checking
        # later)
        rotated = True

        stdout.write(
            "\nSource grid is rotated with pole at ({0:.2f} E {1:.2f} N)\n  "
            "Rotated request ({2:.2f} E {3:.2f} N) to ({4:.2f} E {5:.2f} N)\n"
            .format(pole_lon, pole_lat,
                    sw_lon % 360.0, sw_lat,
                    ne_lon % 360.0, ne_lat))

    # Make sure the longitudes are in the range 0-360
    sw_lon = sw_lon % 360.0
    ne_lon = ne_lon % 360.0

    # Get the grid spacing and the first value of the P-grid
    dx = ff_src.real_constants.col_spacing
    dy = ff_src.real_constants.row_spacing
    zx = ff_src.real_constants.start_lon % 360.0
    zy = ff_src.real_constants.start_lat

    # Get the grid staggering
    if ff_src.fixed_length_header.grid_staggering not in GRID_STAGGER:
        msg = "Grid staggering {0} not supported"
        raise ValueError(msg.format(
            ff_src.fixed_length_header.grid_staggering))
    stagger = GRID_STAGGER[ff_src.fixed_length_header.grid_staggering]

    # Adjust the starting indices if required (does not apply to EG ancils)
    if stagger == "endgame" and ff_src.fixed_length_header.dataset_type != 4:
        zx += 0.5*dx
        zy += 0.5*dy

    # Work out the appropriate X arguments for cutout; if the grid is
    # a wrapping grid account for the area possibly spanning the meridian
    wrapping = (ff_src.fixed_length_header.horiz_grid_type % 100) != 3
    if wrapping:
        if ne_lon < sw_lon:
            ne_lon += 360.0

    x_start = int(np.floor(((sw_lon - zx) % 360.0)/dx)) + 1
    x_points = int(np.ceil(((ne_lon - sw_lon) % 360.0)/dx)) + 1

    y_start = int(np.floor((sw_lat - zy)/dy)) + 1
    y_points = int(np.ceil((ne_lat - sw_lat)/dy)) + 1

    # If these points were calculated from a rotated grid, the transformation
    # applied above might have pushed the request beyond the limits of the
    # source grid - reel the request back in here to avoid problems
    if rotated:
        # If the request breaches the lower edges of the source domain,
        # change it to begin at the start of the domain
        if x_start < 1:
            stdout.write("  X lower boundary exceeded by {0} points, "
                         "adjusting...\n".format(-x_start))
            x_points = x_points + x_start
            x_start = 1
        if y_start < 1:
            stdout.write("  Y lower boundary exceeded by {0} points, "
                         "adjusting...\n".format(-y_start))
            y_points = y_points + y_start
            y_start = 1

        # Similarly, if the request (after the adjustment above) breaches the
        # upper edges of the source domain, change it to stop at those edges
        nx = ff_src.integer_constants.num_cols
        ny = ff_src.integer_constants.num_rows
        if not wrapping and x_start + x_points - 1 > nx:
            stdout.write(
                "  X upper boundary exceeded by {0} points, adjusting...\n"
                .format(x_start + x_points - 1 - nx))
            x_points = nx - x_start + 1
        if y_start + y_points - 1 > ny:
            stdout.write(
                "  Y upper boundary exceeded by {0} points, adjusting...\n"
                .format(y_start + y_points - 1 - ny))
            y_points = ny - y_start + 1

    stdout.write("\n")

    return cutout(ff_src, x_start, y_start, x_points, y_points, stdout)


def cutout(ff_src, x_start, y_start, x_points, y_points, stdout=None):
    """
    Cutout a sub-region from a :class:`mule.FieldsFile` object, based on
    a set of indices describing the region's location in the original file.

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
        * stdout:
            The open file-like object to write informational output to,
            default is to use sys.stdout.

    .. Warning::
        The input :class:`mule.FieldsFile` must be on a fixed
        resolution grid (see the TRIM utility for working with a
        variable grid)

    """
    # Setup printing
    if stdout is None:
        stdout = sys.stdout

    def check_regular_grid(dx, dy, fail_context, mdi=0.0):
        # Raise error if dx or dy values indicate an 'irregular' grid.
        invalid_values = [0.0, mdi]
        if dx in invalid_values or dy in invalid_values:
            msg = "Source grid in {0} is not regular."
            raise ValueError(msg.format(fail_context))

    # Determine the grid staggering
    if ff_src.fixed_length_header.grid_staggering not in GRID_STAGGER:
        msg = "Grid staggering {0} not supported"
        raise ValueError(msg.format(
            ff_src.fixed_length_header.grid_staggering))
    stagger = GRID_STAGGER[ff_src.fixed_length_header.grid_staggering]

    # Remove empty fields before processing
    ff_src.remove_empty_lookups()

    stdout.write(_banner("Extracting sub-region")+"\n")

    stdout.write(
        "Requested region:\n"
        "  X: cutout {0} points from index {1}\n"
        "  Y: cutout {2} points from index {3}\n"
        .format(x_points, x_start, y_points, y_start))

    # Cutout *cannot* continue without the STASHmaster
    if ff_src.stashmaster is None:
        msg = "Cannot cutout from file without a valid STASHmaster"
        raise ValueError(msg)

    # Get the value of real MDI (Note: ancil files don't set it)
    if ff_src.fixed_length_header.dataset_type == 4:
        rmdi = mule._REAL_MDI
    else:
        rmdi = ff_src.real_constants.real_mdi

    # Grid-spacing in degrees, ensure this is a regular grid
    dx = ff_src.real_constants.col_spacing
    dy = ff_src.real_constants.row_spacing
    check_regular_grid(dx, dy, fail_context='header', mdi=rmdi)

    # Want to extract the co-ords of the first P point in the file
    if (stagger == "new_dynamics" or (stagger == "endgame" and
         ff_src.fixed_length_header.dataset_type == 4)):
        # For ND grids and EG ancils this is given directly
        zy0 = ff_src.real_constants.start_lat
        zx0 = ff_src.real_constants.start_lon
    elif stagger == "endgame":
        # For EG grids the P grid is offset by half a grid spacing
        zy0 = ff_src.real_constants.start_lat + 0.5*dy
        zx0 = ff_src.real_constants.start_lon + 0.5*dx

    # Number of points making up the (P) grid
    nx0 = ff_src.integer_constants.num_cols
    ny0 = ff_src.integer_constants.num_rows

    stdout.write(
        "\nSource grid is {0}x{1} points starting at ({2:.2f}E {3:.2f}N)\n"
        .format(nx0, ny0,
                ff_src.real_constants.start_lon,
                ff_src.real_constants.start_lat))

    # Ensure the requested points fit within the target domain (it is allowed
    # to exceed the domain in the X direction provided the domain wraps)
    horiz_grid = ff_src.fixed_length_header.horiz_grid_type
    msg = ("The given cutout parameters extend outside the dimensions of the "
           "grid contained in the source file.")
    if y_start + y_points - 1 > ny0 or (x_start + x_points - 1 > nx0 and
                                        horiz_grid % 100 == 3):
        raise ValueError(msg)

    # Create a new fieldsfile to store the cutout fields
    ff_dest = ff_src.copy()

    # Calculate new file headers describing the cutout domain
    if (stagger == "new_dynamics" or (stagger == "endgame" and
         ff_dest.fixed_length_header.dataset_type == 4)):
        # For ND grids and EG ancils this is given directly
        ff_dest.real_constants.start_lat = zy0 + (y_start - 1)*dy
        ff_dest.real_constants.start_lon = zx0 + (x_start - 1)*dx
    elif stagger == "endgame":
        # For EG grids the header values are offset by half a grid spacing
        ff_dest.real_constants.start_lat = zy0 + ((y_start - 1.5) * dy)
        ff_dest.real_constants.start_lon = zx0 + ((x_start - 1.5) * dx)

    # The new grid type will be a LAM, and its size is whatever the size of
    # the specified cutout domain is going to be.  Remember to preserve the
    # rotated/non-rotated status of the grid
    ff_dest.fixed_length_header.horiz_grid_type = 100*(horiz_grid//100) + 3
    ff_dest.integer_constants.num_cols = x_points
    ff_dest.integer_constants.num_rows = y_points

    stdout.write(
        "Extracted grid is {0}x{1} points starting at ({2:.2f}E {3:.2f}N)\n"
        .format(x_points, y_points, ff_dest.real_constants.start_lon,
                ff_dest.real_constants.start_lat))

    stdout.write("Performing cutout...\n")

    # Ready to begin processing of each field
    for i_field, field_src in enumerate(ff_src.fields):

        # Discard any fields which aren't from a valid release header, since
        # we need to be able to assume certain attributes are present later
        if field_src.lbrel not in (2, 3):
            msg = ('Field {0} has release number {1}, which cutout does not '
                   'support; this field will not appear in the output')
            warnings.warn(msg.format(i_field, field_src.lbrel))
            continue

        # Ensure this field is on a regular grid
        check_regular_grid(field_src.bdx, field_src.bdy,
                           fail_context='Field {0}'.format(i_field),
                           mdi=field_src.bmdi)

        # In case the field has extra data, abort
        if field_src.lbext != 0:
            msg = ('Field {0} has extra data, which cutout '
                   'does not support')
            raise ValueError(msg.format(i_field))

        # If the grid is not a regular lat-lon grid, abort
        if field_src.lbcode % 10 != 1:
            msg = ('Field {0} is not on a regular lat/lon grid')
            raise ValueError(msg.format(i_field))

        # Retrieve the grid-type for this field from the STASHmaster and
        # use it to adjust the indices to extract for the non-P grids
        if field_src.stash is not None:
            grid_type = field_src.stash.grid
        else:
            msg = ("Field {0} STASH code ({1}) not found in STASHmaster; "
                   "this field will not appear in the output")
            warnings.warn(msg.format(i_field, field_src.lbuser4))
            continue

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
    # Setup help text
    help_prolog = """    usage:
      %(prog)s [-h] [--stashmaster STASHMASTER] {indices,coords} ...

    This script will extract a sub-region from a UM FieldsFile, producing
    a new file.
    """
    title = _banner(
        "CUTOUT-II - Cutout tool for UM Files, version II "
        "(using the Mule API)", banner_char="=")

    # Setup the parser
    parser = argparse.ArgumentParser(
        usage=argparse.SUPPRESS,
        description=title + textwrap.dedent(help_prolog),
        formatter_class=argparse.RawTextHelpFormatter,
        )

    parser.add_argument(
        "--stashmaster",
        help="either the full path to a valid stashmaster file, or a UM \n"
        "version number e.g. '10.2'; if given a number cutout will look in \n"
        "the path defined by: \n"
        "  mule.stashmaster.STASHMASTER_PATH_PATTERN \n"
        "which by default is : \n"
        "  $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A\n")

    # The cutout command has 2 forms; the user may describe the region using
    # a series of indices or using the co-ordinates of two opposing corners
    subparsers = parser.add_subparsers()

    # Options for indices
    sub_prolog = """    usage:
      {0} indices [-h] input_file output_file zx zy nx ny

    The index based version of the script will extract a domain
    of whole points defined by the given start indices and lengths
               """.format(os.path.basename(sys.argv[0]))

    parser_index = subparsers.add_parser(
        "indices", formatter_class=argparse.RawTextHelpFormatter,
        description=title + textwrap.dedent(sub_prolog),
        usage=argparse.SUPPRESS,
        help="cutout by indices (run \"%(prog)s indices --help\" \n"
        "for specific help on this command)\n ")

    parser_index.add_argument("input_file", help="File containing source\n ")
    parser_index.add_argument("output_file", help="File for output\n ")

    parser_index.add_argument(
        "zx", type=int,
        help="the starting x (column) index of the region to cutout from \n"
        "the source file\n ")

    parser_index.add_argument(
        "zy", type=int,
        help="the starting y (row) index of the region to cutout from \n"
        "the source file\n ")

    parser_index.add_argument(
        "nx", type=int,
        help="the number of x (column) points to cutout from the source "
        "file\n ")

    parser_index.add_argument(
        "ny", type=int,
        help="the number of y (row) points to cutout from the source file\n")

    # Options for co-ordinates
    sub_prolog = """    usage:
      {0} coords [-h] [--native-grid]
               input_file output_file SW_lon SW_lat NE_lon NE_lat

    The co-ordinate based version of the script will extract a domain
    of whole points which fit within the given corner points
               """.format(os.path.basename(sys.argv[0]))

    parser_coords = subparsers.add_parser(
        "coords", formatter_class=argparse.RawTextHelpFormatter,
        description=title + textwrap.dedent(sub_prolog),
        usage=argparse.SUPPRESS,
        help="cutout by coordinates (run \"%(prog)s coords --help\" \n"
        "for specific help on this command)\n")

    parser_coords.add_argument("input_file", help="File containing source\n ")
    parser_coords.add_argument("output_file", help="File for output\n ")

    parser_coords.add_argument(
        "--native-grid", action="store_true",
        help="if set, cutout will take the provided co-ordinates to be on \n"
        "the file's native grid (otherwise it will assume they are regular \n"
        "co-ordinates and apply any needed rotations automatically). \n"
        "Therefore it does nothing for non-rotated grids\n ")

    parser_coords.add_argument(
        "SW_lon", type=float,
        help="the longitude of the South-West corner point of the region \n"
        "to cutout from the source file\n ")

    parser_coords.add_argument(
        "SW_lat", type=float,
        help="the latitude of the South-West corner point of the region \n"
        "to cutout from the source file\n ")

    parser_coords.add_argument(
        "NE_lon", type=float,
        help="the longitude of the North-East corner point of the region \n"
        "to cutout from the source file\n ")

    parser_coords.add_argument(
        "NE_lat", type=float,
        help="the latitude of the North-East corner point of the region \n"
        "to cutout from the source file\n")

    # If the user supplied no arguments, print the help text and exit
    if len(sys.argv) == 1:
        parser.print_help()
        parser.exit(1)

    args = parser.parse_args()

    # Print version information
    print(_banner("(CUTOUT-II) Module Information")),
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
            msg = "File {0} is a pp file, which cutout does not support"
            raise ValueError(msg.format(filename))

        # Load the file using Mule - filter it according to the file types
        # which cutout can handle
        ff = mule.load_umfile(filename, stashmaster=stashm)
        if ff.fixed_length_header.dataset_type not in (1, 2, 3, 4):
            msg = (
                "Invalid dataset type ({0}) for file: {1}\nCutout is only "
                "compatible with FieldsFiles (3), Dumps (1|2) and Ancils (4)"
                .format(ff.fixed_length_header.dataset_type, filename))
            raise ValueError(msg)

        # Perform the cutout
        if hasattr(args, "zx"):
            ff_out = cutout(ff, args.zx, args.zy, args.nx, args.ny)

        else:
            ff_out = cutout_coords(ff,
                                   args.SW_lon, args.SW_lat,
                                   args.NE_lon, args.NE_lat,
                                   args.native_grid)

        # Write the result out to the new file
        ff_out.to_file(args.output_file)

    else:
        msg = "File not found: {0}".format(filename)
        raise ValueError(msg)


if __name__ == "__main__":
    _main()
