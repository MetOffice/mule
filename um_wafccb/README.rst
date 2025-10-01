Mule is a Python package providing an interface to the various files used 
and produced by the Met Office Unified Model (UM).

This "um_wafccb" module provides a Python extension from the UM WAFC CB
library.  (note that the UM WAFC CB library itself is obtainable via a 
UM licence and must be installed separately).

Building the extension
======================
The first step is to build the extension module; you must link against the 
UM WAFC CB library here, so it should be installed beforehand (the UM 
documentation paper X04 contains details on how to do this, or your site may 
already have a central install).  Once you have located the install save the
path to a variable (as we will need it multiple times):

    DIR=/path/to/the/um/wafccb/library

(The above path should be the one containing the "include" and "lib" 
subdirectories, with the "libum_wafccb.so" shared object present in "lib")

Then use the following command to build the extension:

    python setup.py build_ext --inplace -I$DIR/include -L$DIR/lib -R$DIR/lib


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

    echo $PWD/lib > ~/.local/lib/python2.7/site-packages/um_wafccb.pth

(Note the above instructions assume that the "python" command used in the
earlier steps was relating to python2.7; if not the path above should be 
updated to the correct version).

With the above file in place you should have access to the module.  If your 
site also has a central install of the "um_wafccb" module this will override
it and use the code from your working copy instead.  Remove the file above to 
disable this override and revert to the previous load-path.

API Documentation
=================
Since the extension only exposes a single simple functions please refer to the 
docstrings for the exposed functions (which will be repeated below):

     um_sstpert.sstpert(...)
        Generate WAFC CB diagnostics.

        Usage:
          um_wafccb.um_wafccb(cpnrt, blkcld, concld, ptheta, rmdi, icao_out)

        Args:
        * cpnrt    - Convective Precipitation Rate (2d array).
        * blkcld   - Bulk Cloud Fraction (3d array).
        * concld   - Convective Cloud Amount (3d array).
        * ptheta   - Theta Level Pressure (3d array).
        * rmdi     - Missing Data Indicator.
        * icao_out - Return ICAO heights instaed of pressures if True.

        Returns:
        A tuple containing 3 2d numpy.ndarrays, as follows:
        * p_cbb  - Cb Base Pressure / ICAO Height (if icao_out is True).
        * p_cbt  - Cb Top Pressure / ICAO Height (if icao_out is True).
        * cbhore - Cb Horizontal Extent.




