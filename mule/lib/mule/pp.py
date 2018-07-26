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
This module provides tools for interacting with "pp" files.

"""
from __future__ import (absolute_import, division, print_function)

import six
import mule
import numpy as np

GRID_STAGGER = {3: "new_dynamics", 6: "endgame"}


# Borrow the Mule field class, since a Field in a pp file is essentially the
# same as a Field in a UM file; but adjust the data types since it is 32-bit
class PPField(mule.Field):
    DTYPE_INT = ">i4"
    DTYPE_REAL = ">f4"


# As above but with header release 2 headers
class PPField2(PPField, mule.Field2):
    pass


# As above but with header release 3 headers
class PPField3(PPField, mule.Field3):
    pass

# Mapping to go from release number to field object
FIELD_SELECT = {2: PPField2, 3: PPField3}

# Create mappings for the lbpack n3-n1 digits (similar to how the mule file
# classes contain mappings like these).  The only real difference is that the
# "Unpacked" provider uses the 32-bit class (since PP files are 32-bit)
_READ_PROVIDERS = {
    "000": mule.ff._ReadFFProviderCray32Packed,
    "001": mule.ff._ReadFFProviderWGDOSPacked,
    }

_WRITE_OPERATORS = {
    "000": mule.ff._WriteFFOperatorCray32Packed(),
    "001": mule.ff._WriteFFOperatorWGDOSPacked(),
    }


def file_is_pp_file(file_path):
    """
    Checks to see if a given file is a pp file.

    Args:
        * file_path:
            Path to the file to be checked.

    Returns:
        * True if file is a pp file, False otherwise.

    """
    # The logic behind this is that the first 32-bit word of a pp file should
    # be the record length of the first record (a lookup entry).  Since this
    # has 64, 4-byte words we check to see if it is 64*4 = 256.  In a regular
    # UM File the first 64-bit word should be either 15, 20 or IMDI, and in
    # each of these cases it is not possible for the first half of the word
    # to be 256, making this a safe way to detect a pp file.
    first_word = np.fromfile(file_path, dtype=">i4", count=1)
    return first_word == 256


def fields_from_pp_file(pp_file_obj_or_path):
    """
    Reads in a PP file as a list of field objects.

    Args:
        * pp_file_obj_or_path:
            Either an (opened) file object, or the path
            to a file containing the pp data.

    Returns:
        * pp_fields
            List of :class:`mule.pp.PPField` objects.

    """
    if isinstance(pp_file_obj_or_path, six.string_types):
        pp_file = open(pp_file_obj_or_path, "rb")
    else:
        pp_file = pp_file_obj_or_path

    field_count = 0
    fields = []
    while True:
        # Increment counter
        field_count += 1

        # Read the record length
        reclen = np.fromfile(pp_file, ">i4", 1)

        # Check for end of file
        if len(reclen) == 0:
            break
        else:
            reclen = reclen[0]

        if reclen != 256:
            msg = "Field {0}; Incorrectly sized lookup record: {1}"
            raise ValueError(msg.format(field_count, reclen))

        # Read the record (the header)
        ints = np.fromfile(pp_file, ">i4", mule.Field.NUM_LOOKUP_INTS)
        reals = np.fromfile(pp_file, ">f4", mule.Field.NUM_LOOKUP_REALS)

        # Read the check record
        reclen_check = np.fromfile(pp_file, ">i4", 1)[0]

        # They should match
        if reclen != reclen_check:
            msg = "Field {0}; Inconsistent header record lengths: {1} and {2}"
            raise ValueError(msg.format(field_count, reclen, reclen_check))

        # Load into the basic field class
        field_ref = PPField(ints, reals, None)

        # Use the release number to select a better class if possible
        fclass = FIELD_SELECT.get(field_ref.lbrel, None)
        if fclass is not None:
            field_ref = fclass(ints, reals, None)

        # Read the record length for the data
        reclen = np.fromfile(pp_file, ">i4", 1)[0]

        # This should be equivalent to lbnrec, but can sometimes be set to
        # zero... so to allow the existing provider to work add this value
        # to the reference field's headers
        field_ref.lbnrec = reclen//4

        # Associate the provider
        offset = pp_file.tell()

        # Strip just the n1-n3 digits from the lbpack value
        # and check for a suitable write operator
        lbpack321 = "{0:03d}".format(field_ref.lbpack -
                                     ((field_ref.lbpack//1000) % 10)*1000)

        if lbpack321 not in _READ_PROVIDERS:
            msg = "Field{0}; Cannot interpret unsupported packing code {1}"
            raise ValueError(msg.format(field_count, lbpack321))

        provider = _READ_PROVIDERS[lbpack321](field_ref, pp_file, offset)
        field = type(field_ref)(ints, reals, provider)

        # Now check if the field contains extra data
        if field.lbext > 0:
            # Skip past the field data only (relative seek to avoid overflows)
            pp_file.seek((field.lblrec - field.lbext)*4, 1)

            # Save the current file position
            start = pp_file.tell()

            # Now load in the vectors as they are encountered until the
            # end of the record is reached
            vectors = {}
            ext_consumed = 0
            while pp_file.tell() - start < field.lbext*4:

                # First read the code
                vector_code = np.fromfile(pp_file, ">i4", 1)[0]

                # Split the code into its parts
                vector_points = vector_code // 1000
                vector_type = vector_code % 1000

                # Then read the vector into the dictionary
                vectors[vector_type] = (
                    np.fromfile(pp_file, ">f4", vector_points))

                ext_consumed += vector_points

            # Having finished populating the vectors dict, attach it
            # to the field object
            field.pp_extra_data = vectors

        else:
            # If there isn't any extra data simply
            # Skip the whole record (relative seek here to avoid overflows)
            field.pp_extra_data = None
            pp_file.seek(reclen, 1)

        # Read the check record
        reclen_check = np.fromfile(pp_file, ">i4", 1)[0]
        # They should match
        if reclen != reclen_check:
            msg = "Field {0}; Inconsistent data record lengths; {1} and {2}"
            raise ValueError(msg.format(field_count, reclen, reclen_check))

        fields.append(field)

    pp_file.close()
    return fields


def fields_to_pp_file(pp_file_obj_or_path, field_or_fields, umfile=None):
    """
    Writes a list of field objects to a PP file.

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

    """
    if isinstance(pp_file_obj_or_path, six.string_types):
        pp_file = open(pp_file_obj_or_path, "wb")
    else:
        pp_file = pp_file_obj_or_path

    for field in list(field_or_fields):

        if field.lbrel not in (2, 3):
            continue

        # Similar to the mule file classes, the unpacking of data can be
        # skipped if the packing and accuracy are unchanged and the fields
        # were already PP fields
        if (field._can_copy_deferred_data(field.lbpack, field.bacc) and
           isinstance(field, PPField)):

            # Get the raw bytes containing the data
            data_bytes = field._get_raw_payload_bytes()

        else:
            # If the field has been modified follow a similar set of steps to
            # the mule file classes
            lbpack321 = "{0:03d}".format(field.lbpack -
                                         ((field.lbpack//1000) % 10)*1000)

            if lbpack321 not in _WRITE_OPERATORS:
                msg = "Cannot write out packing code {0}"
                raise ValueError(msg.format(lbpack321))

            data_bytes, _ = _WRITE_OPERATORS[lbpack321].to_bytes(field)

            field.lblrec = len(data_bytes)//4
            field.lbnrec = len(data_bytes)//4

        # If the field appears to be variable resolution, attach the
        # relevant extra data (requires that a UM file object was given)
        vector = {}
        if (field.bzx == field.bmdi or
                field.bzy == field.bmdi or
                field.bdx == field.bmdi or
                field.bdy == field.bmdi):

            # The variable resolution data can either be already attached
            # to the field (most likely if it has already come from an existing
            # pp file) or be supplied via a umfile object + STASH entry...

            if (hasattr(field, "pp_extra_data") and
                    field.pp_extra_data is not None):
                vector = field.pp_extra_data
                extra_len = 6 + 3*field.lbnpt + 3*field.lbrow
            else:
                if umfile is None:
                    msg = ("Variable resolution field/s found, but no "
                           "UM file object provided")
                    raise ValueError(msg)
                if not hasattr(field, "stash"):
                    msg = ("Variable resolution field/s found, but no "
                           "STASH information attached to field objects")
                    raise ValueError(msg)

                stagger = GRID_STAGGER[
                    umfile.fixed_length_header.grid_staggering]
                grid_type = field.stash.grid
                rdc = umfile.row_dependent_constants
                cdc = umfile.column_dependent_constants

                # Calculate U vectors
                if grid_type == 18:  # U points
                    vector[1] = cdc.lambda_u
                    if stagger == "new_dynamics":
                        vector[12] = cdc.lambda_p
                        vector[13] = np.append(cdc.lambda_p[1:-1],
                                               [2.0*cdc.lambda_u[-1] -
                                                cdc.lambda_p[-1]])
                    elif stagger == "endgame":
                        vector[12] = np.append([2.0*cdc.lambda_u[0] -
                                                cdc.lambda_p[0]],
                                               cdc.lambda_p[:-1])
                        vector[13] = cdc.lambda_p
                else:  # Any other grid types
                    vector[1] = cdc.lambda_p
                    if stagger == "new_dynamics":
                        vector[12] = np.append([2.0*cdc.lambda_p[1] -
                                                cdc.lambda_v[1]],
                                               cdc.lambda_u[1:])
                        vector[13] = cdc.lambda_u
                    elif stagger == "endgame":
                        vector[12] = cdc.lambda_u
                        vector[13] = np.append(cdc.lambda_u[1:],
                                               [2.0*cdc.lambda_p[-1] -
                                               cdc.lambda_u[-1]])

                # Calculate V vectors
                if grid_type == 19:  # V points
                    vector[2] = rdc.phi_v
                    if stagger == "new_dynamics":
                        vector[14] = rdc.phi_p
                        vector[15] = np.append(rdc.phi_p[1:],
                                               [2.0*rdc.phi_v[-1] -
                                                rdc.phi_p[-1]])
                    elif stagger == "endgame":
                        vector[14] = np.append([2.0*rdc.phi_v[0] -
                                                rdc.phi_p[0]],
                                               rdc.phi_p[:-1])
                        vector[15] = np.append(rdc.phi_p[:-1],
                                               [2.0*rdc.phi_v[-1] -
                                                rdc.phi_p[-1]])
                else:  # Any other grid types
                    vector[2] = rdc.phi_p[:-1]
                    if stagger == "new_dynamics":
                        vector[14] = np.append([2.0*rdc.phi_p[0] -
                                                rdc.phi_v[0]],
                                               rdc.phi_v[1:])
                        vector[15] = np.append(rdc.phi_v[:-1],
                                               [2.0*rdc.phi_p[-1] -
                                                rdc.phi_v[-1]])
                    elif stagger == "endgame":
                        vector[14] = rdc.phi_v[:-1]
                        vector[15] = rdc.phi_v[1:]

                # Work out extra data sizes and adjust the headers accordingly
                extra_len = 6 + 3*field.lbnpt + 3*field.lbrow
                field.lbext = extra_len
                field.lblrec += extra_len

        # Convert the numbers from the lookup to 32-bit
        ints = field._lookup_ints.astype(">i4")
        reals = field._lookup_reals.astype(">f4")

        # Calculate the record length (pp files are not direct-access, so each
        # record begins and ends with its own length)
        lookup_reclen = np.array((len(ints) + len(reals))*4).astype(">i4")

        # Write the first record (the field header)
        pp_file.write(lookup_reclen)
        pp_file.write(ints)
        pp_file.write(reals)
        pp_file.write(lookup_reclen)

        # Similarly echo the record length before and after the data
        reclen = len(data_bytes)

        if vector:
            reclen += extra_len*4
            keys = [1, 2, 12, 13, 14, 15]
            sizes = ([field.lbnpt, field.lbrow] +
                     [field.lbnpt]*2 + [field.lbrow]*2)

        pp_file.write(np.array(reclen).astype(">i4"))
        pp_file.write(data_bytes)
        if vector:
            for key, size in zip(keys, sizes):
                pp_file.write(np.array(1000*size + key).astype(">i4"))
                pp_file.write(vector[key].astype(">f4"))
        pp_file.write(np.array(reclen).astype(">i4"))
    pp_file.close()
