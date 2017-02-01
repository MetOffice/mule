Version (Report module paths)
=============================

This is a simple utility which is designed to report which versions of the
Python modules related to UM utilities (``mule``, ``um_utils`` and a suitable
packing library module) are currently in use.  Its intended use is to be a 
quick check when developing utility code and overriding the system modules,
or for traceability in other scripts (for example all of the other utilities
call this one at the beginning of their operation). An install of this module
will include an executable wrapper script ``mule-version`` which provides a
command-line interface to Version's functionality, but it may also be imported
and used directly inside another Python script.

Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-version --help``):

.. code-block:: none

    ====================================================================
    * VERSION - Check which version of mule related modules are in use *
    ====================================================================
    usage:
      mule-version [-h]

    optional arguments:
      -h, --help  show this help message and exit
                

um_utils.version API
--------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.version
   :members:
   :show-inheritance:
