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

    usage: mule-fixframe [options]

    FixFrame takes a MakeBC generated frame file and produces a CreateBC
    compatible frame file.

    positional arguments:
      /path/to/input.file   First argument is the path and name of the MakeBC 
                            frames file to be fixed
                        
      /path/for/output.file
                            Second argument is the path and name of the CreateBC
                            frames file to be produced
                        

    optional arguments:
      -h, --help            show this help message and exit



um_utils.fixframe API
---------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.fixframe
   :members:
   :show-inheritance:
