#!/bin/bash
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
#
# Mule, UM packing extension and UM library installation script
#
# In most cases the modules can be directly installed via the usual 
# python setuptools methods.  However in some cases this might not be 
# possible, so this script instead builds all 3 modules to a dummy
# install location in a temporary directory and then copies the 
# results to the chosen destinations.
#
set -eu

if [ $# -lt 3 ] ; then
    echo "USAGE: "
    echo "   $(basename $0) <lib_dest> <bin_dest> <packing_lib>"
    echo ""
    echo "   Must be called from the top-level of a working "
    echo "   copy of the UM mule project, containing the 3"
    echo "   module folders (um_packing, um_utils and mule)"
    echo ""
    echo "ARGS: "
    echo "  * <lib_dest>"
    echo "      The destination directory for the 3 "
    echo "      libraries to be installed to."
    echo "  * <bin_dest>"
    echo "      The destination directory for the "
    echo "      UM utility execs to be installed to."
    echo "  * <packing_lib>"
    echo "      The location of the UM packing library"
    echo "      for linking the um_packing extension."
    echo ""
    echo "  After running the script the directory "
    echo "  named in <lib_dest> should be suitable to "
    echo "  add to python's path via a .pth file, and "
    echo "  after doing this the execs in <bin_dest> "
    echo "  should become functional."
    echo ""
    exit 1
fi

LIB_DEST=$1
BIN_DEST=$2
PACKING_LIB=$3

# A few hardcoded settings
PYTHONEXEC=${PYTHONEXEC:-python2.7}
SCRATCHDIR=$(mktemp -d)
SCRATCHLIB=$SCRATCHDIR/lib/$PYTHONEXEC/site-packages

# Create install directores - they may already exist but should be 
# empty if they do, also check the modules exist in the cwd
exit=0
for module in "mule" "um_packing" "um_utils" ; do
    mkdir -p $LIB_DEST/$module
    if [ "$(ls -A $LIB_DEST/$module)" ] ; then
        echo "Directory '$LIB_DEST/$module' exists but is non-empty"
        exit=1
    fi
    if [ ! -d ./$module ] ; then
	echo "Directory ./$module not found, is this a working copy?"
	exit=1
    fi
done
if [ $exit -eq 1 ] ; then
    echo "Please ensure install directories are clear and re-start"
    echo "from the top level of a UM mule project working copy"
    exit 1
fi

# Likewise for the directory for binaries
mkdir -p $BIN_DEST
if [ "$(ls $BIN_DEST/mule-* 2> /dev/null)" ] ; then
  echo "Execs already exist in '$BIN_DEST'"
  echo "Please ensure these are removed and re-start"
  exit 1
fi

# Check the packing lib is found
if [ ! -d $PACKING_LIB ] ; then
  echo "Packing library directory '$PACKING_LIB' not found"
  exit 1
fi

# Make a temporary directory to hold the installs
mkdir -p $SCRATCHLIB 
ln -s $SCRATCHDIR/lib $SCRATCHDIR/lib64

# The install command will complain if this directory isn't on the path
# so add it to the path here
export PYTHONPATH=${PYTHONPATH-""}:$SCRATCHLIB

# Save a reference to the top-level directory
wc_root=$(pwd)

#------------------------------#
# Building the packing library #
#------------------------------#
# Packing library first
echo "Changing directory to packing module:" $wc_root/um_packing
cd $wc_root/um_packing

echo "Building packing module..."
$PYTHONEXEC setup.py build_ext --inplace \
   -I$PACKING_LIB/include -L$PACKING_LIB/lib -lum_packing -R$PACKING_LIB/lib


#----------------------------------------------#
# Temporary installation to scratch directory  #
#----------------------------------------------#
function install(){
    module=$1
    echo "Changing directory to $module module:" $wc_root/$module
    cd $wc_root/$module

    echo "Installing $module module to $SCRATCHDIR"
    $PYTHONEXEC setup.py install --prefix $SCRATCHDIR
}
    
install um_packing
install mule
install um_utils

#------------------------------------------------------------#
# Extraction and copying of files to destination directories #
#------------------------------------------------------------#
function unpack_and_copy(){
    module=$1
    egg=$SCRATCHLIB/$module*.egg

    # The egg might be zipped - if it is unzip it in place
    if [ ! -d $egg ] ; then
      echo "Unpacking zipped egg..."
      unzip_dir=$SCRATCHLIB/${module}_unzipped_egg
      unzip $egg -d $unzip_dir
      egg=$unzip_dir
    fi  

    destdir=$LIB_DEST/$module
    echo "Installing $module to $destdir"
    mkdir -p $destdir
    cp -vr $egg/$module/* $destdir

    # For the execs, also copy these to the bin directory
    if [ $module == "um_utils" ] ; then
        echo "Installing $module execs and info to $BIN_DEST/"
        cp -vr $egg/EGG-INFO $BIN_DEST/$module.egg-info        
        cp -vr $SCRATCHDIR/bin/* $BIN_DEST/
    fi
}

unpack_and_copy um_packing
unpack_and_copy mule
unpack_and_copy um_utils

# Cleanup the temporary directory
echo "Cleaning up temporary directory: $SCRATCHDIR"
rm -rf $SCRATCHDIR