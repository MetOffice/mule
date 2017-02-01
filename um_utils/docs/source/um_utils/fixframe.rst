Fixframe (Convert MakeBC frame to CreateBC frame)
=================================================

This utility is used to convert an old style MakeBC frame file into a CreateBC 
compatible frame file.  An install of this module will include an executable 
wrapper script ``mule-fixframe`` which provides a command-line interface to 
fixframe's functionality, but it may also be imported and used directly inside
another Python script.

Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-fixframe --help``):

.. code-block:: none

    ===========================================================================
    * FIXFRAME - Converter for old-style UM frames files (Using the Mule API) *
    ===========================================================================
    usage:
      mule-fixframe [-h] input_filename output_filename

    This script will take a MakeBC generated frame file and produce
    a CreateBC compatible frame file.

    positional arguments:
      input_filename   First argument is the path and name of the MakeBC frames file 
                       to be fixed

      output_filename  Second argument is the path and name of the CreateBC frames 
                       file to be produced

    optional arguments:
      -h, --help       show this help message and exit


um_utils.fixframe API
---------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.fixframe
   :members:
   :show-inheritance:
