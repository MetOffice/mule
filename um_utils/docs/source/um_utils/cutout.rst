Cutout (Extract subregion from fixed resolution file)
=====================================================

This utility is used to specify a region from within an existing UM file and
have it extracted and written to a new file.  This is useful when the full UM
domain isn't required for some downstream task, which might be analysis, 
visualisation or just storage.  An install of this module will include an
executable wrapper script ``mule-cutout`` which provides a command-line 
interface to most of Cutout's functionality, but it may also be imported and
used directly inside another Python script.

.. Warning::

    Note that this utility is designed to work on **fixed resolution files**,
    if you are trying to work with a variable resolution file you should
    first investigate using the ``mule-trim`` utility.


Command line utility
--------------------
Here is the help text for the command line utility (obtainable by running
``mule-cutout --help``):

.. code-block:: none

    =========================================================================
    * CUTOUT-II - Cutout tool for UM Files, version II (using the Mule API) *
    =========================================================================
    usage:
      mule-cutout [-h] [--stashmaster STASHMASTER] {indices,coords} ...

    This script will extract a sub-region from a UM FieldsFile, producing
    a new file.

    positional arguments:
      {indices,coords}
        indices             cutout by indices (run "mule-cutout indices --help" 
                            for specific help on this command)

        coords              cutout by coordinates (run "mule-cutout coords --help" 
                            for specific help on this command)

    optional arguments:
      -h, --help            show this help message and exit
      --stashmaster STASHMASTER
                            either the full path to a valid stashmaster file, or a UM 
                            version number e.g. '10.2'; if given a number cutout will look in 
                            the path defined by: 
                              mule.stashmaster.STASHMASTER_PATH_PATTERN 
                            which by default is : 
                              $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A


Note that as shown above the command has two modes of operation - ``indices`` 
and ``coords``, with each requiring different arguments.  Here are the help
texts for these two modes:

(from ``mule-cutout indices --help``):

.. code-block:: none

    =========================================================================
    * CUTOUT-II - Cutout tool for UM Files, version II (using the Mule API) *
    =========================================================================
    usage:
      mule-cutout indices [-h] input_file output_file zx zy nx ny

    The index based version of the script will extract a domain
    of whole points defined by the given start indices and lengths

    positional arguments:
      input_file   File containing source

      output_file  File for output

      zx           the starting x (column) index of the region to cutout from 
                   the source file

      zy           the starting y (row) index of the region to cutout from 
                   the source file

      nx           the number of x (column) points to cutout from the source file

      ny           the number of y (row) points to cutout from the source file

    optional arguments:
      -h, --help   show this help message and exit
         
(from ``mule-cutout coords --help``):

.. code-block:: none

    =========================================================================
    * CUTOUT-II - Cutout tool for UM Files, version II (using the Mule API) *
    =========================================================================
    usage:
      mule-cutout coords [-h] [--native-grid]
               input_file output_file SW_lon SW_lat NE_lon NE_lat

    The co-ordinate based version of the script will extract a domain
    of whole points which fit within the given corner points

    positional arguments:
      input_file     File containing source

      output_file    File for output

      SW_lon         the longitude of the South-West corner point of the region 
                     to cutout from the source file

      SW_lat         the latitude of the South-West corner point of the region 
                     to cutout from the source file

      NE_lon         the longitude of the North-East corner point of the region 
                     to cutout from the source file

      NE_lat         the latitude of the North-East corner point of the region 
                     to cutout from the source file

    optional arguments:
      -h, --help     show this help message and exit
      --native-grid  if set, cutout will take the provided co-ordinates to be on 
                     the file's native grid (otherwise it will assume they are regular 
                     co-ordinates and apply any needed rotations automatically). 
                     Therefore it does nothing for non-rotated grids


um_utils.cutout API
-------------------
Here is the API documentation (auto-generated):

.. automodule:: um_utils.cutout
   :members:
   :special-members: __init__
   :show-inheritance:
