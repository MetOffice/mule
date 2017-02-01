Trim (Extract fixed region from a variable grid)
================================================

This utility is used to trim a fixed resolution area from a 
**variable resolution** file away.  Variable resolution files are typically 
divided into 9 fixed resolution regions (though they don't have to be).  The
intended use of this utility is to allow one of these sections to be turned 
into a standalone fixed resolution file for further processing.  An install
of this module will include an executable wrapper script ``mule-trim`` which 
provides a command-line interface to most of Trim's functionality, but it may
also be imported and used directly inside another Python script.

Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-trim --help``):

.. code-block:: none

    =========================================================================
    * TRIM - Fixed region extraction tool for UM Files (using the Mule API) *
    =========================================================================
    usage:
      mule-trim [-h] [options] input_file output_file region_x region_y

    This script will extract a fixed-grid sub-region from a variable
    resolution UM FieldsFile, producing a new file.

    positional arguments:
      region_x              the x index of the *region* to extract, starting from 1. 
                            In a typical variable resolution FieldsFile the central region 
                            will be given by '2'

      region_y              the y index of the *region* to extract, starting from 1. 
                            In a typical variable resolution FieldsFile the central region 
                            will be given by '2'

    optional arguments:
      -h, --help            show this help message and exit
      --stashmaster STASHMASTER
                            either the full path to a valid stashmaster file, or a UM 
                            version number e.g. '10.2'; if given a number trim will look in 
                            the path defined by: 
                              mule.stashmaster.STASHMASTER_PATH_PATTERN 
                            which by default is: 
                              $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A


um_utils.trim API
-----------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.trim
   :members:
   :show-inheritance:
