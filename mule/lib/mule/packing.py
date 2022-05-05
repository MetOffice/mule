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
Methods for packing and unpacking the data payloads of UM file fields.

This module will use *either* the SHUMlib packing library wrapper module
"um_packing", *or* the slower implementation "mo_pack"; whichever is installed.

*   "um_packing" provides a wrapper to the SHUMlib packing library.
        This is the faster option and is the same library used by the UM.
*   "mo_pack" is a wrapper to the "libmo_unpack" C library implementation.
        These are both open-source software, available from :
        https://github.com/SciTools/mo_pack and
        https://github.com/SciTools/libmo_unpack.

    .. note::
        The "libmo_unpack" library has some known limitations :
        It does not produce identical results to the SHUMlib library;
        it is substantially slower; and it is limited to 32-bit floating-point
        accuracy.

"""
import os
import pkgutil

# First establish whether the SHUMlib packing library is available
if not pkgutil.get_loader("um_packing") is None:
    try:
        import um_packing
        # Since the SHUMlib packing employs OpenMP for speed, make sure the
        # environment variable which controls the number of threads is set
        # (on some platforms the default will be a high number of threads
        # which can cause issues - we set it to be single threaded by default)
        _omp_threads = "OMP_NUM_THREADS"
        if (_omp_threads not in os.environ or
                not os.environ[_omp_threads].isdigit()):
            os.environ[_omp_threads] = "1"

        def _wgdos_unpack_field(data_bytes, mdi, rows, cols):
            """
            Unpack a WGDOS-packed field using the SHUMlib packing library.

            Args:
                * data_bytes (string):
                    the raw byte data in the file.  This should be exactly as
                    read in from the file (so without any byte-swapping or
                    other processing).
                * mdi (float):
                    the value used as missing data in the field.
                * rows, cols (int):
                    not used by this implementation.

            Returns:
                data (array):
                    the unpacked 2-dimensional data payload.

            """
            data = um_packing.wgdos_unpack(data_bytes, mdi)
            return data

        def _wgdos_pack_field(data, mdi, acc):
            """
            WGDOS-pack a field using the SHUMlib packing library.

            Args:
                * data (array):
                    a 2-dimensional array containing the field data.

                    .. note::
                        this must be a contiguous array; some slices and other
                        array views may be unsuitable to pass here.

                * mdi (float):
                    the value representing missing data in the field.
                * acc (int):
                   the accuracy to pack the field to.  This a power of 2 so,
                   expect the packed values to be within (2**acc)/2 above or
                   below the original values.

            Returns:
                data_bytes (string):
                    packed byte data.

            """
            data_bytes = um_packing.wgdos_pack(data, mdi, acc)
            return data_bytes

    except ImportError as err:
        msg = "SHUMlib Packing library found, but failed to import"
        raise ImportError(err.args + (msg,))

elif not pkgutil.get_loader("mo_pack") is None:
    # If the UM library wasn't found, try the MO packing library instead
    try:
        import mo_pack

        def _wgdos_unpack_field(data_bytes, mdi, rows, cols):
            """
            Unpack a WGDOS-packed field using the MO packing library 'mo_pack'.

            Args:
                * data_bytes (string):
                    the raw byte data in the file.  This should be exactly as
                    read in from the file (so without any byte-swapping or
                    other processing).
                * mdi (float):
                    the value used as missing data in the field.
                * rows, cols (int):
                    the number of expected rows and columns in the unpacked
                    field.

            Returns:
                data (array):
                    the unpacked 2-dimensional data payload.

            """
            data = mo_pack.decompress_wgdos(data_bytes, rows, cols, mdi)
            return data

        def _wgdos_pack_field(data, mdi, acc):
            """
            WGDOS-pack a field using the MO packing library 'mo_pack'.

            Args:
                * data (array):
                    a 2-dimensional array containing the field data.
                    .. note::
                        this must be a contiguous array; some slices and other
                        array views may be unsuitable to pass here.
                * mdi (float):
                    the value representing missing data in the field.
                * acc (int):
                   the accuracy to pack the field to.  This a power of 2 so,
                   expect the packed values to be within (2**acc)/2 above or
                   below the original values.

            Returns:
                data_bytes (string):
                    packed byte data.

            """
            data_buffer = mo_pack.compress_wgdos(data.astype("f4"), acc, mdi)
            data_bytes = data_buffer.tobytes()
            return data_bytes

    except ImportError as err:
        msg = "MO Packing library found, but failed to import"
        raise ImportError(err.args + (msg,))

else:
    # If neither the UM nor MO libraries were found, fall-back to placeholders
    # which will allow the API to function, but will not be able to perform
    # any actual unpacking
    def _wgdos_unpack_field(data_bytes, mdi, rows, cols):
        """
        Unpack WGDOS packed field placeholder - this will be used when
        no other suitable packing library has been loaded, it cannot
        perform any unpacking.  Please see the documentation for details
        of how to obtain a valid packing library.

        """
        msg = "No WGDOS packing library available, unable to unpack field"
        raise NotImplementedError(msg)

    def _wgdos_pack_field(data, mdi, acc):
        """
        WGDOS pack field placeholder - this will be used when no other
        suitable packing library has been loaded, it cannot perform any
        packing.  Please see the documentation for details of how to obtain
        a valid packing library.

        """
        msg = "No WGDOS packing library available, unable to pack field"
        raise NotImplementedError(msg)


def wgdos_unpack_field(data_bytes, mdi, rows, cols):
    """
    Unpack a WGDOS-packed field.

    Args:
        * data_bytes (string):
            the raw byte data in the file.  This should be exactly as read
            in from the file (so without any byte-swapping or other
            processing).
        * mdi (float):
            the value used as missing data in the field.
        * rows, cols (int):
            the number of expected rows and columns in the unpacked field.

            .. note::
                these parameters are ignored by the "um_packing"
                implementation.

    Returns:
        data (array):
            the unpacked 2-dimensional data payload.

    """
    return _wgdos_unpack_field(data_bytes, mdi, rows, cols)


def wgdos_pack_field(data, mdi, acc):
    """
    WGDOS-pack a field.

    Args:
        * data (array):
            a 2-dimensional array containing the field data.

            .. note::
                this must be a contiguous array; some slices and other
                array views may be unsuitable to pass here.

        * mdi (float):
            the value representing missing data in the field.
        * acc (int):
           the accuracy to pack the field to.  This a power of 2, so expect
           the packed values to be within (2**acc)/2 above or below the
           original values.

    Returns:
        data_bytes (string):
            packed byte data.

    """
    data_bytes = _wgdos_pack_field(data, mdi, acc)
    return data_bytes
