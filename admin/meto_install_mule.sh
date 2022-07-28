#!/bin/bash

set -eu

# Note: The way this script is intended to work is that you should first
# load whatever modules or setup you wish to do to ensure that when you
# run "python" at the command line (i.e. exactly the command "python")
# it accesses the version of Python which you are intended to create a
# Mule install for.  At the Met Office this would mean once for the
# system's own Python and then again to cover the various "scitools"
# versions (some of which might use the same copy of Python + Numpy)
#
# So for instance suppose you want to create a new install for the
# latest "default-current" scitools environment:
#
#    module load scitools/default-current
#    ./meto_install_mule.sh
#
# If, for example default-current currently is using Python 3.8 with
# Numpy 12.10 this will create a new directory called
#    python-3.8_numpy-12.10
#
# Which you should then tell the modulefiles to load when the user
# has the default-current environment loaded
#
# It is intended that this script is run from the directory containing
# the Mule installs in $UMDIR i.e. $UMDIR/mule/mule-YYYY.MM.V/ so that
# the above directories all appear there.  Since it uses the
# library-lock functionality of Mule's install script you *must* build
# Mule directly into the destination and not copy it there afterwards

# Setup what version of things should be used

# Mule version for build (will be checked out from SRS)
mule_ver=2022.07.1
# UM version for sstpert and wafccb libraries (will be looked up in $UMDIR)
um_ver=vn13.0
# Shumlib version (will be looked up in $UMDIR)
shum_ver=2022.7.1

# Set library locations and which specific builds to use on each platform
hostname=$(hostname)
if [[ $hostname == uan01 ]] ; then  # EXZ
  shum=$UMDIR/shumlib/shumlib-$shum_ver/meto-ex1a-crayftn-14.0.0-craycc-14.0.0
  sst=$UMDIR/$um_ver/ex1a/sstpert_cce
  wafc=$UMDIR/$um_ver/ex1a/wafccb_cce

elif [[ $hostname == xc* ]] ; then  # XC40
  # Use ivybridge chipset as we want these things to be able to work interactively
  # on the login nodes
  module swap craype-haswell craype-ivybridge
  shum=$UMDIR/shumlib/shumlib-$shum_ver/meto-xc40-ivybridge-crayftn-8.4.3-craycc-8.4.3
  sst=$UMDIR/$um_ver/xc40/sstpert_cce
  wafc=$UMDIR/$um_ver/xc40/wafccb_cce

else  # Desktop/SPICE
  ulimit -s unlimited
  module swap ifort/16.0_64
  shum=$UMDIR/shumlib/shumlib-$shum_ver/meto-x86-ifort-16.0.1-gcc-4.4.7
  sst=$UMDIR/$um_ver/linux/sstpert_gcc_ifort
  wafc=$UMDIR/$um_ver/linux/wafccb_gcc_ifort
fi

# Get a copy of the mule trunk at the required version - if it has already been
# checked out, re-use the copy already present.  Note that this leaves a working
# copy in the current directory, which you may want to clean up once finished
if [ ! -d mule_trunk_$mule_ver ] ; then
  fcm co fcm:mule.xm_tr@$mule_ver mule_trunk_$mule_ver
fi
cd mule_trunk_$mule_ver

# Find out the versions of Python and Numpy the environment has
pythonver=$(python -c "from platform import python_version ; print(python_version())")
numpyver=$(python -c "import numpy; print(numpy.__version__)")

# Construct the name of the install directory for this Mule install
dest_dir=python-${pythonver}_numpy-${numpyver}
# Don't overwrite/rebuild an existing install
if [ -d $dest_dir ] ; then
    echo "$dest_dir already exists..."
    exit 1
fi

# Run the build twice - once with and once without openmp
for omp in openmp no-openmp ; do

    # Mule's install script, with all of the optional features enabled
    # (this is a central install so we want everything)
    admin/install_mule.sh \
        --library_lock --ppibm_lib --spiral_lib \
        --sstpert_lib $sst --wafccb_lib $wafc \
        ../$dest_dir/$omp/lib ../$dest_dir/$omp/bin $shum/$omp

    # Check the build works by running the unit-tests
    for mod in um_packing mule um_utils um_spiral_search ; do
        PYTHONPATH=../$dest_dir/$omp/lib python -m unittest discover -v $mod.tests
    done

    # By default the entry-point scripts created this way will be tied to
    # the specific interpreter used.  The way we side-load Mule into the
    # environment means that we'd prefer if they just work with whatever
    # python resolves to (under the assumption that they are always going
    # to be called when a compatible environment is loaded; which the
    # modules we setup make sure of).  So we'll replace the first line of
    # the entry point scripts with the generic environment python invocation
    sed -i "s:^#!.*:#!/usr/bin/env python:g" ../$dest_dir/$omp/bin/mule-*

done
