Mule is a Python package providing an interface to the various files used 
and produced by the Met Office Unified Model (UM).

This "um_packing" module provides a Python extension from the SHUMlib packing
library, which Mule can optionally make use of (the SHUMlib library is also 
freely available - hopefully from the same location as you obtained Mule)

Building the extension
======================
The first step is to build the extension module; you must link against the 
SHUMlib packing library here, so it should be installed beforehand (the 
documentation included in SHUMlib contains details on how to do this, or your 
site may already have a central install).  Once you have located the install 
save the path to a variable (as we will need it multiple times):

    DIR=/path/to/the/shumlib/library

(The above path should be the one containing the "include" and "lib"
subdirectories, with several libraries including "libshum_wgdos_packing.so" 
shared object present in "lib")

Then use the following command to build the extension:

    python setup.py build_ext --inplace \
             -I$DIR/include -L$DIR/lib -R$DIR/lib

Installation (Central)
======================
These steps explain how to install the library to your central (root) Python
installation directory.  If you are developing changes to the module or 
otherwise need to access it without the required root access to install it 
in this way, see the "Development/User" section below instead.

Once the extension has been built (see above) the module can be built and
installed:

    python setup.py build 
    python setup.py install

The python setuptools methodology used here supports a variety of additional 
options which you can use to customise the install process, including the
location of the installed files.  Please consult the setuptools documentation
for further information.


Installation (Development/User)
===============================
If you wish to make the module available without installing it, the recommended 
method is to make use of Python's "pth" functionality.  Before you can do this 
you must first build the module (see above).

Override Python's load path for the module to pick up the lib directory of
this package:

    echo $PWD/lib > ~/.local/lib/python2.7/site-packages/um_packing.pth

(Note the above instructions assume that the "python" command used in the
earlier steps was relating to python2.7; if not the path above should be 
updated to the correct version).

With the above file in place you should have access to the module.  If your 
site also has a central install of the "um_packing" module this will override
it and use the code from your working copy instead.  Remove the file above to 
disable this override and revert to the previous load-path.


Testing
=======
Once installed via one of the methods above you can test the library with the 
following command:

    python -m unittest discover -v um_packing.tests

This should run 3 tests which will ensure the library is working.


Other configuration
===================
The SHUMlib packing library supports OpenMP - if it was compiled with OpenMP 
support enabled you may control the number of threads the library uses by
setting the environment variable OMP_NUM_THREADS.  (The Mule module which
imports this library defaults this variable to "1" if it is not set, for safety).


API Documentation
=================
Since the extension only exposes a few simple functions please refer to the 
docstrings for the exposed functions (which will be repeated below):

    um_packing.wgdos_pack(...)
        Pack a UM field using WGDOS packing.

        Usage:
          um_packing.wgdos_pack(field_in, mdi, accuracy)

        Args:
        * field_in - 2 Dimensional numpy.ndarray containing the field.
        * mdi      - Missing data indicator.
        * accuracy - Packing accuracy (power of 2).

        Returns:
          Byte-array/stream (suitable to write straight to file).

    um_packing.wgdos_unpack(...)
        Unpack UM field data which has been packed using WGDOS packing.

        Usage:
           um_packing.wgdos_unpack(bytes_in, mdi)

        Args:
        * bytes_in - Packed field byte-array.
        * mdi      - Missing data indicator.

        Returns:
          2 Dimensional numpy.ndarray containing the unpacked field.

    um_packing.get_um_version(...)
        Return the UM version number used to compile the library.

        Returns:
          String containing the UM version number.

