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


def validate_dataset_type(umf, dt_valid, filename=None):
    """
    Check that a :class:`UMFile` object has an accepted dataset_type.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * dt_valid:
            A tuple containing valid values of the dataset type
            to be checked against.

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    dt_found = umf.fixed_length_header.dataset_type
    if dt_found not in dt_valid:
        msg = "Incorrect dataset_type (found {0}, should be one of {1})"
        raise ValidateError(filename, msg.format(dt_found, dt_valid))


def validate_grid_staggering(umf, gs_valid, filename=None):
    """
    Check that a :class:`UMFile` object has an accepted grid staggering.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * gs_valid:
            A tuple containing valid values of the grid staggering
            to be checked against.

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    gs_found = umf.fixed_length_header.grid_staggering
    if gs_found not in gs_valid:
        msg = ("Unsupported grid_staggering (found {0}, can support "
               "one of {1})")
        raise ValidateError(filename, msg.format(gs_found, gs_valid))


def validate_integer_constants(umf, ic_valid, filename=None):
    """
    Check that integer constants associated with a :class:`UMFile` object
    are present and the expected size.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * ic_valid:
            The expected number of integer constants to be checked against.

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    if umf.integer_constants is None:
        raise ValidateError(
            filename, "Integer constants not found")
    ic_length = umf.integer_constants.shape[0]
    if ic_length != ic_valid:
        msg = ("Incorrect number of integer constants, "
               "(found {0}, should be {1})")
        raise ValidateError(filename, msg.format(ic_length, ic_valid))


def validate_real_constants(umf, rc_valid, filename=None):
    """
    Check that real constants associated with a :class:`UMFile` object
    are present and the expected size.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * rc_valid:
            The expected number of real constants to be checked against.

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    if umf.real_constants is None:
        raise ValidateError(
            filename, "Real constants not found")
    rc_length = umf.real_constants.shape[0]
    if rc_length != rc_valid:
        msg = ("Incorrect number of real constants, "
               "(found {0}, should be {1})")
        raise ValidateError(filename, msg.format(rc_length, rc_valid))


def validate_level_dependent_constants(umf, ldc_valid, filename=None):
    """
    Check that level dependent constants associated with a
    :class:`UMFile` object are present and the expected size.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * ldc_valid:
            Tuple containing the size of the two expected dimensions
            of the level dependent constants to be checked against.

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    if umf.level_dependent_constants is None:
        raise ValidateError(
            filename, "Level dependent constants not found")

    ldc_shape = umf.level_dependent_constants.shape
    if ldc_shape != ldc_valid:
        msg = ("Incorrectly shaped level dependent constants based on "
               "file type and number of levels in integer_constants "
               "(found {0}, should be {1})")
        raise ValidateError(filename, msg.format(ldc_shape, ldc_valid))


def validate_row_dependent_constants(umf, rdc_valid, filename=None):
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

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    rdc_shape = umf.row_dependent_constants.shape
    if rdc_shape != rdc_valid:
        msg = ("Incorrectly shaped row dependent constants based on "
               "file type and number of rows in integer_constants "
               "(found {0}, should be {1})")
        raise ValidateError(filename, msg.format(rdc_shape, rdc_valid))


def validate_column_dependent_constants(umf, cdc_valid, filename=None):
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

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    cdc_shape = umf.column_dependent_constants.shape
    if cdc_shape != cdc_valid:
        msg = ("Incorrectly shaped column dependent constants based "
               "on file type and number of columns in "
               "integer_constants (found {0}, should be {1})")
        raise ValidateError(filename, msg.format(cdc_shape, cdc_valid))


def validate_variable_resolution_field(umf, field, ifield, filename=None):
    """
    Check the grid-specific lookup headers from a field in a variable
    resolution file.  These must agree with the row + column dependent
    constants, and the fixed grid lookup headers must be set to RMDI.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * field:
            A :class:`Field` subclass instance.
        * ifield:
            The index of the field for use in any raised exception.

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    # Note since we don't have the STASHmaster to refer to the best
    # we can do is to allow a +/- 1 tolerance on the agreement between
    # the sizes reported by the file and the lookup (due to the various
    # different grid-offsets present in the model)
    col_diff = np.abs(field.lbnpt -
                      umf.integer_constants.num_cols)
    if col_diff > 1:
        msg = ("Field {0} column count inconsistent with "
               "variable resolution grid constants")
        raise ValidateError(filename, msg.format(ifield))

    row_diff = np.abs(field.lbrow -
                      umf.integer_constants.num_rows)
    if row_diff > 1:
        msg = ("Field {0} row count inconsistent with "
               "variable resolution grid constants")
        raise ValidateError(filename, msg.format(ifield))

    # If the file defines RMDI, use it, otherwise use the global
    # definition from the main Mule module
    if hasattr(umf.real_constants, "real_mdi"):
        rmdi = umf.real_constants.real_mdi
    else:
        rmdi = mule._REAL_MDI

    # Fields on variable grids should have these values (specific to
    # fixed resolution grids) set to RMDI
    if field.bzx != rmdi:
        msg = ("Field {0} start longitude (bzx) not RMDI "
               "in variable resolution file")
        raise ValidateError(filename, msg.format(ifield))
    if field.bzy != rmdi:
        msg = ("Field {0} start latitude (bzy) not RMDI "
               "in variable resolution file")
        raise ValidateError(filename, msg.format(ifield))
    if field.bdx != rmdi:
        msg = ("Field {0} longitude interval (bdx) not RMDI "
               "in variable resolution file")
        raise ValidateError(filename, msg.format(ifield))
    if field.bdy != rmdi:
        msg = ("Field {0} latitude interval (bdy) not RMDI "
               "in variable resolution file")
        raise ValidateError(filename, msg.format(ifield))


def validate_regular_field(umf, field, ifield, filename=None):
    """
    Check the grid-specific lookup headers from a field in a fixed
    resolution file.  The file defines the model domain and it is
    expected that the field should cover the same area.

    Args:
        * umf:
            A :class:`UMFile` subclass instance.
        * field:
            A :class:`Field` subclass instance.
        * ifield:
            The index of the field for use in any raised exception.

    Kwargs:
        * filename:
            If this check is associated with a file on disk the
            name can be passed here to appear in any exceptions.

    """
    # For normal fields, the easiest way to get an idea of if
    # all grid aspects are right is to check that the field's
    # definition of the grid extent matches the file's
    lon_start_diff_steps = (
        np.abs(field.bzx + field.bdx
               - umf.real_constants.start_lon) / field.bdx)

    field_end_lon = field.bzx + field.lbnpt*field.bdx
    file_end_lon = (umf.real_constants.start_lon +
                    umf.integer_constants.num_cols *
                    umf.real_constants.col_spacing)
    lon_end_diff_steps = (
        np.abs(field_end_lon - file_end_lon) / field.bdx)

    # For the longitude the field's results must be within 1.0
    # grid-spacing of the P grid in the header (allow an
    # additional 1% tolerance for rounding errors)
    if (lon_end_diff_steps > 1.01 or
            lon_start_diff_steps > 1.01):
        msg = ("Field {0} grid longitudes inconsistent\n"
               "File grid: {1} to {2}, spacing {3}\n"
               "Field {0} grid: {4} to {5}, spacing {6}\n"
               "Extents should be within 1 field grid-spacing")
        raise ValidateError(
            filename, msg.format(
                ifield, umf.real_constants.start_lon,
                file_end_lon, umf.real_constants.col_spacing,
                field.bzx + field.bdx, field_end_lon,
                field.bdx))

    # And repeat the same tests for the latitudes
    lat_start_diff_steps = (
        np.abs(field.bzy + field.bdy
               - umf.real_constants.start_lat) / field.bdy)

    field_end_lat = field.bzy + field.lbrow*field.bdy
    file_end_lat = (umf.real_constants.start_lat +
                    umf.integer_constants.num_rows *
                    umf.real_constants.row_spacing)
    lat_end_diff_steps = (
        np.abs(field_end_lat - file_end_lat) / field.bdy)

    # Similarly for the latitudes 1.0 grid spacing with a
    # 1% tolerance
    if (lat_end_diff_steps > 1.01 or
            lat_start_diff_steps > 1.01):
        msg = ("Field {0} grid latitudes inconsistent\n"
               "File grid: {1} to {2}, spacing {3}\n"
               "Field {0} grid: {4} to {5}, spacing {6}\n"
               "Extents should be within 1 field grid-spacing")
        raise ValidateError(
            filename, msg.format(
                ifield, umf.real_constants.start_lat,
                file_end_lat, umf.real_constants.row_spacing,
                field.bzy + field.bdy, field_end_lat,
                field.bdy))
