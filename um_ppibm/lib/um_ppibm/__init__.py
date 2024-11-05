# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# This file is part of the SHUMlib packing library extension module for Mule.
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
This module is a modified version of the writing routine of "pp.py" from
the main Mule module.  The difference is that the data written out is passed
through a data conversion routine (from Shumlib) that converts the data
into a 32-bit IBM number format.  The reason for this is to replicate some
behaviour of a legacy piece of code at the Met Office (convpp), so it is
likely of little real use outside of that case.

"""
from __future__ import (absolute_import, division, print_function)

import six
import mule
import mule.pp
import numpy as np
import struct

try:
    from .um_ieee2ibm32 import ieee2ibm32, get_shumlib_version
except ImportError as err:
    msg = "Failed to import ieee2ibm32 extension"
    raise ImportError(err.args + (msg,))

__version__ = "2024.11.1"


# Custom write operator for "unpacked" fields which passes them through the
# IEEE2IBM32 conversion
class _WriteIBMOperatorUnpacked(object):
    def to_bytes(self, field):
        data = field.get_data()
        data_ibm = ieee2ibm32(data.astype("f8"))
        return data_ibm, len(data_ibm)


# Replace the write operator in the usual pp.py list with the one above
_WRITE_OPERATORS = mule.pp._WRITE_OPERATORS.copy()
_WRITE_OPERATORS["000"] = _WriteIBMOperatorUnpacked()


def fields_to_pp_file_ibm32(
        pp_file_obj_or_path, field_or_fields,
        umfile=None, keep_addressing=False):
    """
    Writes a list of field objects to a PP file, in IBM format.

    Args:
        * pp_file_obj_or_path:
            Either an (opened) file object, or the path
            to a file where the pp data should be written.
        * field_or_fields:
            A list of :class:`mule.Field` subclass instances
            to be written to the file.
        * umfile:
            If the fields being written contain data on a variable
            resolution grid, provide a :class:`mule.UMFile` subclass
            instance here to add the row + column dependent
            constant information to the pp field "extra data".
        * keep_addressing:
            Whether or not to preserve the values of LBNREC, LBEGIN
            and LBUSER(2) from the original file - these are not used
            by pp files so by default will be set to zero.

    """
    if isinstance(pp_file_obj_or_path, six.string_types):
        pp_file = open(pp_file_obj_or_path, "wb")
    else:
        pp_file = pp_file_obj_or_path

    for field in list(field_or_fields):

        if field.lbrel not in (2, 3):
            continue

        # Skip unpacking if possible (but only for WGDOS fields, since all
        # unpacked fields need their number format converting)
        if (field.lbpack == 1 and field._can_copy_deferred_data(
                field.lbpack, field.bacc, mule.pp.PP_WORD_SIZE)):
            # Get the raw bytes containing the data
            data_bytes = field._get_raw_payload_bytes()
            # Remove any padding
            true_len = struct.unpack(">i", data_bytes[:4])[0]
            data_bytes = data_bytes[:true_len*4]

        else:
            # Get the required part of the packing code
            lbpack321 = "{0:03d}".format(field.lbpack
                                         - ((field.lbpack
                                             // 1000) % 10) * 1000)

            # Don't defer unpacking (as in the normal class)
            if lbpack321 not in _WRITE_OPERATORS:
                msg = "Cannot write out packing code {0}"
                raise ValueError(msg.format(lbpack321))

            data_bytes, _ = _WRITE_OPERATORS[lbpack321].to_bytes(field)

        # Calculate LBLREC
        field.lblrec = len(data_bytes) // mule.pp.PP_WORD_SIZE

        # The return from the ieee2ibm32 needs to be padded in some cases
        # (to ensure whole 64-bit words only)
        if field.lblrec % 2 != 0:
            field.lblrec += 1
            data_bytes += b"\x00\x00\x00\x00"

        # If the field appears to be variable resolution, attach the
        # relevant extra data (requires that a UM file object was given)
        vector = {}
        if (field.bzx == field.bmdi
                or field.bzy == field.bmdi
                or field.bdx == field.bmdi
                or field.bdy == field.bmdi):

            # The variable resolution data can either be already attached
            # to the field (most likely if it has already come from an existing
            # pp file) or be supplied via a umfile object + STASH entry...
            if (hasattr(field, "pp_extra_data")
                    and field.pp_extra_data is not None):
                vector = field.pp_extra_data
                extra_len = 6 + 3 * field.lbnpt + 3 * field.lbrow
            else:
                if umfile is None:
                    msg = ("Variable resolution field/s found, but no "
                           "UM file object provided")
                    raise ValueError(msg)
                if not hasattr(field, "stash"):
                    msg = ("Variable resolution field/s found, but no "
                           "STASH information attached to field objects")
                    raise ValueError(msg)

                stagger = mule.pp.GRID_STAGGER[
                    umfile.fixed_length_header.grid_staggering]
                grid_type = field.stash.grid
                rdc = umfile.row_dependent_constants
                cdc = umfile.column_dependent_constants

                # Calculate U vectors
                if grid_type in (11, 18):  # U points
                    vector[1] = cdc.lambda_u
                    if stagger == "new_dynamics":
                        vector[12] = cdc.lambda_p
                        vector[13] = np.append(cdc.lambda_p[1:-1],
                                               [2.0 * cdc.lambda_u[-1]
                                                - cdc.lambda_p[-1]])
                    elif stagger == "endgame":
                        vector[12] = np.append([2.0 * cdc.lambda_u[0]
                                                - cdc.lambda_p[0]],
                                               cdc.lambda_p[:-1])
                        vector[13] = cdc.lambda_p
                else:  # Any other grid types
                    vector[1] = cdc.lambda_p
                    if stagger == "new_dynamics":
                        vector[12] = np.append([2.0 * cdc.lambda_p[1]
                                                - cdc.lambda_v[1]],
                                               cdc.lambda_u[1:])
                        vector[13] = cdc.lambda_u
                    elif stagger == "endgame":
                        vector[12] = cdc.lambda_u
                        vector[13] = np.append(cdc.lambda_u[1:],
                                               [2.0 * cdc.lambda_p[-1]
                                               - cdc.lambda_u[-1]])

                # Calculate V vectors
                if grid_type in (11, 19):  # V points
                    vector[2] = rdc.phi_v
                    if stagger == "new_dynamics":
                        vector[14] = rdc.phi_p
                        vector[15] = np.append(rdc.phi_p[1:],
                                               [2.0 * rdc.phi_v[-1]
                                                - rdc.phi_p[-1]])
                    elif stagger == "endgame":
                        vector[14] = np.append([2.0 * rdc.phi_v[0]
                                                - rdc.phi_p[0]],
                                               rdc.phi_p[:-1])
                        vector[15] = np.append(rdc.phi_p[:-1],
                                               [2.0 * rdc.phi_v[-1]
                                                - rdc.phi_p[-1]])
                else:  # Any other grid types
                    vector[2] = rdc.phi_p[:-1]
                    if stagger == "new_dynamics":
                        vector[14] = np.append([2.0 * rdc.phi_p[0]
                                                - rdc.phi_v[0]],
                                               rdc.phi_v[1:])
                        vector[15] = np.append(rdc.phi_v[:-1],
                                               [2.0 * rdc.phi_p[-1]
                                                - rdc.phi_v[-1]])
                    elif stagger == "endgame":
                        vector[14] = rdc.phi_v[:-1]
                        vector[15] = rdc.phi_v[1:]

                # Work out extra data sizes and adjust the headers accordingly
                extra_len = 6 + 3 * field.lbnpt + 3 * field.lbrow
                field.lbext = extra_len
                field.lblrec += extra_len

        # (Optionally) zero LBNREC, LBEGIN and LBUSER2, since they have no
        # meaning in a pp file (because pp files have sequential records
        # rather than direct)
        if not keep_addressing:
            field.lbnrec = 0
            field.lbegin = 0
            field.lbuser2 = 0

        # Get the components of the lookup
        ints = field._lookup_ints
        reals = field._lookup_reals

        # Calculate the record length (pp files are not direct-access, so each
        # record begins and ends with its own length)
        lookup_reclen = np.array(
            (len(ints) + len(reals)) * mule.pp.PP_WORD_SIZE).astype(">i4")

        # Write the first record (the field header)
        pp_file.write(lookup_reclen)
        pp_file.write(ieee2ibm32(ints.astype("i8")))
        pp_file.write(ieee2ibm32(reals.astype("f8")))

        pp_file.write(lookup_reclen)

        # Similarly echo the record length before and after the data
        reclen = len(data_bytes)

        if vector:
            reclen += extra_len * mule.pp.PP_WORD_SIZE
            keys = [1, 2, 12, 13, 14, 15]
            sizes = ([field.lbnpt, field.lbrow]
                     + [field.lbnpt] * 2 + [field.lbrow] * 2)

        reclen = np.array(reclen).astype(">i4")
        pp_file.write(reclen)
        pp_file.write(data_bytes)

        if vector:
            for key, size in zip(keys, sizes):
                pp_file.write(ieee2ibm32(
                    np.array(1000 * size + key).astype("i8")))
                pp_file.write(ieee2ibm32(
                    vector[key].astype("f8")))
        pp_file.write(reclen)

    # Add an extra (duplicate) last field with Field Code set to -99
    # (to replicate behaviour of convpp)
    ints[22] = -99
    pp_file.write(lookup_reclen)
    pp_file.write(ieee2ibm32(ints.astype("i8")))
    pp_file.write(ieee2ibm32(reals.astype("f8")))
    pp_file.write(lookup_reclen)
    pp_file.write(reclen)
    pp_file.write(data_bytes)
    pp_file.write(reclen)

    pp_file.close()
