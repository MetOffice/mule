# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of Mule.
#
# Mule is free software: you can redistribute it and/or modify it under
# the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# Mule is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with Mule.  If not, see <http://opensource.org/licenses/BSD-3-Clause>.

"""
This module provides a set of common validation functions.  Generally the
different file classes don't have the exact same requirements, but since a
lot of the validation logic is very similar it is contained here.

"""
from __future__ import (absolute_import, division, print_function)

import mule
import numpy as np


class ValidateError(ValueError):
    """Exception class to raise when validation does not pass."""
    def __init__(self, filename, message):
        msg = "Failed to validate\n"
        if filename is not None:
            msg += "File: {0}\n".format(filename)
        msg += message
        super(ValidateError, self).__init__(msg)


def validate_dataset_type(umf, dt_valid):
    """
    Check that a :class:`UMFile` object has an accepted dataset_type.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * dt_valid:
            A tuple containing valid values of the dataset type
            to be checked against.

    """
    out_msg = []
    dt_found = umf.fixed_length_header.dataset_type
    if dt_found not in dt_valid:
        msg = "Incorrect dataset_type (found {0}, should be one of {1})"
        out_msg = [msg.format(dt_found, dt_valid)]
    return out_msg


def validate_grid_staggering(umf, gs_valid):
    """
    Check that a :class:`UMFile` object has an accepted grid staggering.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * gs_valid:
            A tuple containing valid values of the grid staggering
            to be checked against.

    """
    out_msg = []
    gs_found = umf.fixed_length_header.grid_staggering
    if gs_found not in gs_valid:
        msg = ("Unsupported grid_staggering (found {0}, can support "
               "one of {1})")
        out_msg = [msg.format(gs_found, gs_valid)]
    return out_msg


def validate_integer_constants(umf, ic_valid):
    """
    Check that integer constants associated with a :class:`UMFile` object
    are present and the expected size.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * ic_valid:
            The expected number of integer constants to be checked against.

    """
    out_msg = []
    if umf.integer_constants is None:
        return ["Integer constants not found"]
    ic_length = umf.integer_constants.shape[0]
    if ic_length != ic_valid:
        msg = ("Incorrect number of integer constants, "
               "(found {0}, should be {1})")
        out_msg = [msg.format(ic_length, ic_valid)]
    return out_msg


def validate_real_constants(umf, rc_valid):
    """
    Check that real constants associated with a :class:`UMFile` object
    are present and the expected size.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * rc_valid:
            The expected number of real constants to be checked against.

    """
    out_msg = []
    if umf.real_constants is None:
        return ["Real constants not found"]
    rc_length = umf.real_constants.shape[0]
    if rc_length != rc_valid:
        msg = ("Incorrect number of real constants, "
               "(found {0}, should be {1})")
        out_msg = [msg.format(rc_length, rc_valid)]
    return out_msg


def validate_level_dependent_constants(umf, ldc_valid):
    """
    Check that level dependent constants associated with a
    :class:`UMFile` object are present and the expected size.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * ldc_valid:
            Tuple containing the size of the two expected dimensions
            of the level dependent constants to be checked against.

    """
    out_msg = []
    if umf.level_dependent_constants is None:
        return ["Level dependent constants not found"]

    ldc_shape = umf.level_dependent_constants.shape
    if ldc_shape != ldc_valid:
        msg = ("Incorrectly shaped level dependent constants based on "
               "file type and number of levels in integer_constants "
               "(found {0}, should be {1})")
        out_msg = [msg.format(ldc_shape, ldc_valid)]
    return out_msg


def validate_row_dependent_constants(umf, rdc_valid):
    """
    Check that the row dependent constants associated with a :class:`UMFile`
    object are the expected size.

    .. Note::
        This does not confirm that the constants are present, since
        these constants are optional; the caller must check this separately.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * rdc_valid:
            Tuple containing the size of the two expected dimensions
            of the row dependent constants to be checked against.

    """
    out_msg = []
    rdc_shape = umf.row_dependent_constants.shape
    if rdc_shape != rdc_valid:
        msg = ("Incorrectly shaped row dependent constants based on "
               "file type and number of rows in integer_constants "
               "(found {0}, should be {1})")
        out_msg = [msg.format(rdc_shape, rdc_valid)]
    return out_msg


def validate_column_dependent_constants(umf, cdc_valid):
    """
    Check that the column dependent constants associated with a
    :class:`UMFile` object are the expected size.

    .. Note::
        This does not confirm that the constants are present, since
        these constants are optional; the caller must check this separately.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * cdc_valid:
            Tuple containing the size of the two expected dimensions
            of the column dependent constants to be checked against.

    """
    out_msg = []
    cdc_shape = umf.column_dependent_constants.shape
    if cdc_shape != cdc_valid:
        msg = ("Incorrectly shaped column dependent constants based "
               "on file type and number of columns in "
               "integer_constants (found {0}, should be {1})")
        out_msg = [msg.format(cdc_shape, cdc_valid)]
    return out_msg


def validate_field_grid_type(umf, field):
    """
    Check that the type of grid in the field agrees with the type
    of grid specified by the file.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * field:
            A :class:`Field` subclass instance.

    """
    # If the field has a particularly exotic lbcode value, we can't be
    # sure about the validation
    if field.lbcode not in [1, 101]:
        msg = ("Skipping Field validation due to irregular lbcode: \n"
               "  Field lbcode: {0}")
        return [msg.format(field.lbcode)]

    # Check that if the file specifies a rotated grid, the field does as well
    # (if it doesn't it probably won't validate so skip validation)
    file_rotated = (umf.fixed_length_header.horiz_grid_type > 100)
    field_rotated = (field.lbcode == 101)
    if (file_rotated != field_rotated):
        msg = ("Cannot validate field due to incompatible grid rotation:\n"
               "  File grid rotated  : {0}\n"
               "  Field grid rotated : {1}")
        return [msg.format(file_rotated, field_rotated)]

    # In some cases output fields from the UM contain fields which aren't on
    # the whole domain (a STASH option) - these won't validate so don't try
    file_hem = umf.fixed_length_header.horiz_grid_type % 100
    if (field.lbhem != file_hem and umf.fixed_length_header.dataset_type != 5):
        msg = ("Cannot validate field due to incompatible grid type:\n"
               "  File grid : {0}\n"
               "  Field grid: {1}")
        return [
            msg.format(file_hem, field.lbhem)]


def validate_variable_resolution_field(umf, field):
    """
    Check the grid-specific lookup headers from a field in a variable
    resolution file.  These must agree with the row + column dependent
    constants, and the fixed grid lookup headers must be set to RMDI.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * field:
            A :class:`Field` subclass instance.

    """
    # Check the grid type first; if it isn't compatible return early
    grid_type_msg = validate_field_grid_type(umf, field)
    if grid_type_msg is not None:
        return grid_type_msg

    out_msg = []
    # Variable resolution grids are relatively easy to test - there's no
    # need to use the STASHmaster as the only thing that matters is if the
    # field has the right amount of points for the supplied row and column
    # dependent constants (+/- 1 to handle the various grid offsets)
    col_diff = np.abs(field.lbnpt -
                      umf.integer_constants.num_cols)
    if col_diff > 1:
        msg = ("Field column count inconsistent with "
               "variable resolution grid constants")
        out_msg.append(msg)

    row_diff = np.abs(field.lbrow -
                      umf.integer_constants.num_rows)
    if row_diff > 1:
        msg = ("Field row count inconsistent with "
               "variable resolution grid constants")
        out_msg.append(msg)

    # If the file defines RMDI, use it, otherwise use the global
    # definition from the main Mule module
    if hasattr(umf.real_constants, "real_mdi"):
        rmdi = umf.real_constants.real_mdi
    else:
        rmdi = mule._REAL_MDI

    # Fields on variable grids should have these values (specific to
    # fixed resolution grids) set to RMDI
    if field.bzx != rmdi:
        msg = ("Field start longitude (bzx) not RMDI "
               "in variable resolution file")
        out_msg.append(msg)
    if field.bzy != rmdi:
        msg = ("Field start latitude (bzy) not RMDI "
               "in variable resolution file")
        out_msg.append(msg)
    if field.bdx != rmdi:
        msg = ("Field longitude interval (bdx) not RMDI "
               "in variable resolution file")
        out_msg.append(msg)
    if field.bdy != rmdi:
        msg = ("Field latitude interval (bdy) not RMDI "
               "in variable resolution file")
        out_msg.append(msg)
    return out_msg


def validate_regular_field(umf, field):
    """
    Check the grid-specific lookup headers from a field in a fixed
    resolution file.  This assumes that the field object has a reference
    to a STASHmaster entry; if it does not, or if it is of a type which
    isn't handled explicitly below it will defer to the non-stash version
    of this routine.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * field:
            A :class:`Field` subclass instance.

    """
    # Check the grid type first; if it isn't compatible return early
    grid_type_msg = validate_field_grid_type(umf, field)
    if grid_type_msg is not None:
        return grid_type_msg

    # If the field has no STASH entry, fall back to the simpler type of
    # validation
    if field.stash is None:
        return validate_regular_field_nostash(umf, field)

    # Get the grid staggering as a string
    stagger = ({3: "new_dynamics", 6: "endgame"}
               .get(umf.fixed_length_header.grid_staggering, None))

    # For regular grids need to check the grid dimensions, grid spacing
    # and start positions - do this for known grid types below
    lon_start_exp = umf.real_constants.start_lon
    lat_start_exp = umf.real_constants.start_lat
    lon_spacing_exp = umf.real_constants.col_spacing
    lat_spacing_exp = umf.real_constants.row_spacing
    n_col_exp = umf.integer_constants.num_cols
    n_row_exp = umf.integer_constants.num_rows

    if field.stash.grid in [1, 2, 3, 21, 26, 29]:
        # P (Theta) grid points (incl land/sea masked + LBC versions)
        if stagger == "new_dynamics":
            # Field grid is the same as file grid for ND
            pass
        elif stagger == "endgame":
            # Field grid is half a spacing ahead of file grid in both
            # directions for EG
            lon_start_exp += umf.real_constants.col_spacing/2
            lat_start_exp += umf.real_constants.row_spacing/2
    elif field.stash.grid == 18:
        # U grid points (Non LBC cases)
        if stagger == "new_dynamics":
            # Field grid is same size as file grid but half a spacing
            # ahead in the X-direction only for ND
            lon_start_exp += umf.real_constants.col_spacing/2
        elif stagger == "endgame":
            # Field grid is same size as file grid but half a spacing
            # ahead in the Y-direction only for EG
            lat_start_exp += umf.real_constants.row_spacing/2
    elif field.stash.grid == 27:
        # U grid points (LBC cases only)
        if stagger == "new_dynamics":
            # Field grid has one less point and is half a spacing ahead
            # of file grid in the X-direction only for ND
            lon_start_exp += umf.real_constants.col_spacing/2
            n_col_exp -= 1
        elif stagger == "endgame":
            # Field grid is the same size as file grid by half a spacing
            # ahead in the Y-direction only for EG
            lat_start_exp += umf.real_constants.row_spacing/2
    elif field.stash.grid in [19, 28]:
        # V grid points (in both LBC and non-LBC cases)
        if stagger == "new_dynamics":
            # Field grid has one less point and is half a grid spacing ahead
            # of file grid in the Y-direction only for ND
            lat_start_exp += umf.real_constants.row_spacing/2
            n_row_exp -= 1
        elif stagger == "endgame":
            # Field grid has one more point in the Y-direction and is half a
            # grid spacing ahead in the X-direction than the file grid for EG
            lon_start_exp += umf.real_constants.col_spacing/2
            n_row_exp += 1
    elif field.stash.grid in [11, 12, 13]:
        # UV grid points
        if stagger == "new_dynamics":
            # Field grid has one less point in the Y-direction and is half a
            # grid spacing ahead in both directions than the file grid for ND
            lon_start_exp += umf.real_constants.col_spacing/2
            lat_start_exp += umf.real_constants.row_spacing/2
            n_row_exp -= 1
        elif stagger == "endgame":
            # Field grid has one more point in the Y-direction than the file
            # grid for EG
            n_row_exp += 1
    elif field.stash.grid == 23:
        # River routing grid
        if umf.fixed_length_header.horiz_grid_type != 0:
            return ["Field is river routing diag, which is invalid "
                    "for non-Global domains"]
        else:
            # Note the river routing diagnostics are restriced to a very
            # specific fixed grid; any deviation from this is incorrect
            lon_start_exp = 0.5
            lat_start_exp = -89.5
            n_row_exp = 180
            n_col_exp = 360
            lon_spacing_exp = 1.0
            lat_spacing_exp = 1.0
    else:
        # Other cases are currently un-handled; these include (4) and (5)
        # (Zonal/Meridional theta points), (14) and (15) (Zonal/Meridional
        # UV points), (17) (scalar) and (22) (ozone grid).
        # For these simply defer to the non-STASH enabled routine, which
        # should provide a reasonable validation for these.
        return validate_regular_field_nostash(umf, field)

    # Some fields may be Zonal means, indicated by lbproc - these won't test
    # correctly below so use the non-STASH enabled routine instead
    if field.lbproc & 64 != 0:
        return validate_regular_field_nostash(umf, field)

    # Unless the grid type was unhandled, proceed to perform the
    # comparison below
    out_msg = []
    tol = umf.real_constants.col_spacing*0.001
    if (n_col_exp != field.lbnpt or
            np.abs(lon_spacing_exp - field.bdx) > tol or
            np.abs(lon_start_exp - (field.bzx + field.bdx)) > tol):
        msg = ("Field grid longitudes inconsistent (STASH grid: {0})\n"
               "  File            : {1} points from {2}, spacing {3}\n"
               "  Field (Expected): {4} points from {5}, spacing {3}\n"
               "  Field (Lookup)  : {6} points from {7}, spacing {8}")
        out_msg.append(msg.format(
            field.stash.grid, umf.integer_constants.num_cols,
            umf.real_constants.start_lon,
            umf.real_constants.col_spacing,
            n_col_exp, lon_start_exp,
            field.lbnpt, field.bzx + field.bdx, field.bdx))

    tol = umf.real_constants.row_spacing*0.001
    if (n_row_exp != field.lbrow or
            np.abs(lat_spacing_exp - field.bdy) > tol or
            np.abs(lat_start_exp - (field.bzy + field.bdy)) > tol):
        msg = ("Field grid latitudes inconsistent (STASH grid: {0})\n"
               "  File            : {1} points from {2}, spacing {3}\n"
               "  Field (Expected): {4} points from {5}, spacing {3}\n"
               "  Field (Lookup)  : {6} points from {7}, spacing {8}")
        out_msg.append(msg.format(
            field.stash.grid, umf.integer_constants.num_rows,
            umf.real_constants.start_lat,
            umf.real_constants.row_spacing,
            n_row_exp, lat_start_exp,
            field.lbrow, field.bzy + field.bdy, field.bdy))
    return out_msg


def validate_regular_field_nostash(umf, field):
    """
    Check the grid-specific lookup headers from a field in a fixed
    resolution file.  The file defines the model domain and it is
    expected that the field should cover the same area - which is a
    reasonable way to test should the STASHmaster entry not be available.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * field:
            A :class:`Field` subclass instance.

    """
    # For normal fields, the easiest way to get an idea of if
    # all grid aspects are right is to check that the field's
    # definition of the grid extent matches the file's
    lon_start_diff_steps = (
        np.abs(field.bzx + field.bdx
               - umf.real_constants.start_lon) / field.bdx)

    field_end_lon = field.bzx + field.lbnpt*field.bdx
    file_end_lon = (umf.real_constants.start_lon +
                    (umf.integer_constants.num_cols - 1) *
                    umf.real_constants.col_spacing)
    lon_end_diff_steps = (
        np.abs(field_end_lon - file_end_lon) / field.bdx)

    # For the longitude the field's results must be within 1.0
    # grid-spacing of the P grid in the header (allow an
    # additional 1% tolerance for rounding errors)
    out_msg = []
    if (lon_end_diff_steps > 1.01 or
            lon_start_diff_steps > 1.01):
        msg = ("Field grid longitudes inconsistent\n"
               "  File grid : {0} to {1}, spacing {2}\n"
               "  Field grid: {3} to {4}, spacing {5}\n"
               "  Extents should be within 1 field grid-spacing")
        out_msg.append(msg.format(
            umf.real_constants.start_lon,
            file_end_lon, umf.real_constants.col_spacing,
            field.bzx + field.bdx, field_end_lon,
            field.bdx))

    # And repeat the same tests for the latitudes
    lat_start_diff_steps = (
        np.abs(field.bzy + field.bdy
               - umf.real_constants.start_lat) / field.bdy)

    field_end_lat = field.bzy + field.lbrow*field.bdy
    file_end_lat = (umf.real_constants.start_lat +
                    (umf.integer_constants.num_rows - 1) *
                    umf.real_constants.row_spacing)
    lat_end_diff_steps = (
        np.abs(field_end_lat - file_end_lat) / field.bdy)

    # Similarly for the latitudes 1.0 grid spacing with a
    # 1% tolerance
    if (lat_end_diff_steps > 1.01 or
            lat_start_diff_steps > 1.01):
        msg = ("Field grid latitudes inconsistent\n"
               "  File grid : {0} to {1}, spacing {2}\n"
               "  Field grid: {3} to {4}, spacing {5}\n"
               "  Extents should be within 1 field grid-spacing")
        out_msg.append(msg.format(
            umf.real_constants.start_lat,
            file_end_lat, umf.real_constants.row_spacing,
            field.bzy + field.bdy, field_end_lat,
            field.bdy))
    return out_msg
