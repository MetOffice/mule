Mule is a Python package providing an interface to the various files used 
and produced by the Met Office Unified Model (UM).

This "um_utils" module provides a series of specific utility tools for 
working with UM files.  Most of these tools can be used via a series of
command-line scripts, or imported and used in python.  

Note that most of the scripts rely on being able to unpack and pack UM 
fields, so in addition to the Mule API itself, a suitable packing 
extension must be installed.  Please refer to the documentation and
README for the core Mule module for details.


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

    echo $PWD/lib > ~/.local/lib/python2.7/site-packages/um_utils.pth

(Note the above instructions assume that the desired Python install was 
"python2.7"; if not the path above should be updated to the correct version).

With the above file in place you should have access to the module.  If your 
site also has a central install of the "um_utils" module this will override
it and use the code from your working copy instead.  Remove the file above to 
disable this override and revert to the previous load-path.


Testing
=======
Once installed you can run in-built tests with the following commands.

To test a specific utility, e.g. "pumf" or "cumf":

    python -m unittest discover -v um_utils.tests.pumf
    python -m unittest discover -v um_utils.tests.cumf

Or to run all available tests:

    python -m unittest discover -v um_utils.tests


Other configuration
===================
The SHUMlib packing library supports OpenMP - if your installation is using the 
SHUMlib library and it was compiled with OpenMP support enabled you may control 
the number of threads the library uses by setting the environment variable 
OMP_NUM_THREADS.  (The Mule module which imports this library defaults this
variable to "1" for safety).


API Documentation
=================
This module is documented using Sphinx; once the module is installed change
into the "docs" directory and use the makefile to build the documentation of
your choice (we recommend producing html with "make html" but other options
are available)

