Mule is a Python package providing an interface to the various files used 
and produced by the Met Office Unified Model (UM).

Mule provides read and write access to the headers and data for these Files and 
representations of these in memory.  The UM Documentation paper F03 provides 
the full specification for these data formats.

Packing extension
=================
Note that in order to pack and unpack WGDOS packed UM fields a suitable packing
extension must be installed alongside this module (although some operations
which do not require access to the unpacked data will still work without any
library installed).  There are two choices for this library:

 * The "um_packing" module provides a wrapper to the SHUMlib packing library.  
   This is the same library used by the UM itself to pack and unpack WGDOS
   fields; it should be available from the same location you obtained Mule.
   Refer to the SHUMlib documentation for instructions on building SHUMlib and
   the README for the "um_packing" module for instructions on building 
   the extension from it.

 * The "mo_pack" module provides a wrapper to the "libmo_unpack" C library 
   implementation.  Both the module and the library itself are open-source
   and are available from the SciTools github at:

        https://github.com/SciTools/mo_pack 
        https://github.com/SciTools/libmo_unpack

   Refer to the documentation for each of the above projects for information
   on installing and configuring the extension.


Installation (Central)
======================
These steps explain how to install the module to your central (root) Python
installation directory.  If you are developing changes to the module or 
otherwise need to access it without the required root access to install it 
in this way, see the "Development/User" section below instead.

To build and install the module run the following:

    python setup.py build 
    python setup.py install

The python setuptools methodology used here supports a variety of additional 
options which you can use to customise the install process, including the
location of the installed files.  Please consult the setuptools documentation
for further information.


Installation (Development/User)
===============================
If you wish to make the module available without installing it, the recommended 
method is to make use of Python's "pth" functionality.

Override Python's load path for the module to pick up the lib directory of
this package:

    echo $PWD/lib > ~/.local/lib/python2.7/site-packages/mule.pth

(Note the above instructions assume that the desired Python install was 
"python2.7"; if not the path above should be updated to the correct version).

With the above file in place you should have access to the module.  If your 
site also has a central install of the "mule" module this will override
it and use the code from your working copy instead.  Remove the file above to 
disable this override and revert to the previous load-path.


Testing
=======
Once installed you can run in-built tests with the following command.

    python -m unittest discover -v mule.tests


Other configuration
===================
The SHUMlib packing library supports OpenMP - if your installation is using the 
SHUMlib library and it was compiled with OpenMP support enabled you may control the 
number of threads the library uses by setting the environment variable 
OMP_NUM_THREADS.  (The Mule module which imports this library defaults this
variable to "1" for safety).


API Documentation
=================
This module is documented using Sphinx; once the module is installed change
into the "docs" directory and use the makefile to build the documentation of
your choice (we recommend producing html with "make html" but other options
are available)
