# (C) Crown Copyright 2015, Met Office. All rights reserved.
#
# This file is part of the UM utilities module, which use the Mule API.
#
# Mule and these utilities are free software: you can redistribute it and/or
# modify them under the terms of the Modified BSD License, as published by the
# Open Source Initiative.
#
# These utilities are distributed in the hope that they will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Modified BSD License for more details.
#
# You should have received a copy of the Modified BSD License
# along with these utilities.
# If not, see <http://opensource.org/licenses/BSD-3-Clause>.
"""
This module provides the means to load and interact with the entries in a UM
STASHmaster file.

There are 3 basic ways to load and access the STASHmaster:

 * Load the STASHmaster by providing the path:

   >>> stashm = STASHmaster.from_file('/path/to/STASHmaster_A')

 * Load the STASHmaster from its version number:

   >>> stashm = STASHmaster.from_version('10.2')

 * Load the STASHmaster from the version in a :class:`mule.UMFile` object:

   >>> stashm = STASHmaster.from_umfile(umfile_object)

.. Note:
    In the latter two cases above, it is assumed that a set of UM install
    directories exist in the location defined by the UMDIR environment
    variable (the location of the file is assumed to be
    $UMDIR/vnX.X/ctldata/STASHmaster/STASHmaster_A)

"""
import os
import re
import warnings


class STASHLookupError(KeyError):
    """Exception used when a STASH code lookup has failed."""
    pass


class STASHParseError(ValueError):
    """Exception used when parsing the STASHmaster has failed."""
    pass

# This list corresponds to the valid entries from single STASHmaster record,
# in the order they should appear
_STASH_ENTRY_NAMES = [
    "model",
    "section",
    "item",
    "name",
    "space",
    "point",
    "time",
    "grid",
    "levelT",
    "levelF",
    "levelL",
    "pseudT",
    "pseudF",
    "psuedL",
    "levcom",
    "option_codes",
    "version_mask",
    "halo",
    "dataT",
    "dumpP",
    "packing_codes",
    "rotate",
    "ppf",
    "user",
    "lbvc",
    "blev",
    "tlev",
    "rblevv",
    "cfll",
    "cfff",
    ]

# And these store names for the packing + option codes
_PACKING_CODE_NAMES = ["PC{0:d}".format(i+1) for i in range(9)] + ["PCA"]
_OPTION_CODE_NAMES = ["n{0:d}".format(i+1) for i in range(30)]


class STASHentry(object):
    """Object which stores a single STASHmaster record."""
    def __init__(self, entries):
        """
        Initialise the object.

        Args:
            * entries:
                A list containing the full set of STASHmaster values, in the
                order they appear in the file.

        """
        # Check that the number of entries is correct
        if len(entries) != len(_STASH_ENTRY_NAMES):
            raise STASHParseError("Error parsing STASHmaster (corrupt record)")

        # Go through the names and apply relevant processing
        for iname, name in enumerate(_STASH_ENTRY_NAMES):
            if name == "packing_codes":
                # For the packing codes, expand into a dictionary
                entry = dict(zip(
                    _PACKING_CODE_NAMES, map(int, entries[iname].split())))
            elif name == "option_codes":
                # For the option codes, expand into a dictionary (note the
                # array is reversed here to make sure the labelling is right
                # - since "n30" is actually the first digit)
                entry = dict(zip(
                    _OPTION_CODE_NAMES, map(int, entries[iname][::-1])))
            else:
                # For all normal entries convert them to integers if possible
                if entries[iname].isdigit():
                    entry = int(entries[iname])
                else:
                    entry = entries[iname]
            # Save the entry as a new attribute in this object
            setattr(self, name, entry)

    def __repr__(self):
        return ("<stashmaster._STASHentry object: "
                "SC:{0:5d} - \"{1:s}\">".format(
                    (1000*self.section + self.item), self.name))


class STASHmaster(dict):
    """
    Dictionary-like object which represents a UM STASHmaster file.

    """
    def __init__(self):
        """Initialise an empty STASHmaster object."""
        # Note this object intentionally disables the default
        # init from the parent dictionary object, as we want
        # to maintain control over its creation
        self.filename = None
        pass

    @classmethod
    def from_file(cls, filename):
        """
        Load the STASHmaster from a file.

        * fname:
            The direct path to a valid STASHmaster file.

        """
        if os.path.exists(filename):
            # Read the lines from the file
            with open(filename, 'r') as fh:
                lines = fh.read()

            # The STASHmaster consists of exactly 5 rows of pipe (|)
            # delimited entries, start by extracting the contents of
            # each line in full
            entries = re.findall(r"^1\s*\|(.*)\n"
                                 r"2\s*\|(.*)\n"
                                 r"3\s*\|(.*)\n"
                                 r"4\s*\|(.*)\n"
                                 r"5\s*\|(.*)\|\s*$",
                                 lines, flags=re.MULTILINE)

            # Create an empty STASHmaster object
            stashmaster = cls()
            stashmaster.filename = filename

            for entry in entries:
                # Now split the contents of each entry and use them to create
                # entry objects
                entry_obj = STASHentry(
                    map(str.strip, "".join(entry).split("|")))

                # The file contains an indicator at the end of the file
                if entry_obj.name == "END OF FILE MARK":
                    continue

                # The key should be the STASH code - which is comprised
                # from the combination of the section and item code, use
                # it to save the new entry object to the dictionary
                stashcode = "{0:02d}{1:03d}".format(int(entry_obj.section),
                                                    int(entry_obj.item))
                stashmaster[stashcode] = entry_obj

            return stashmaster

        else:
            msg = "Unable to load STASHmaster, cannot find file: {0}"
            warnings.warn(msg.format(filename))
            return None

    @classmethod
    def from_version(cls, version):
        """
        Load the STASHmaster from a version string.

        Args:
            * version:
                The string giving the version number, e.g '10.2'.

        .. Note:
            The rest of the path will be constructed assuming a standard
            UM install, with environment variable UMDIR as the install
            directory root.

        """
        if 'UMDIR' in os.environ:
            filename = os.path.join(os.environ['UMDIR'],
                                    "vn{0}".format(version),
                                    "ctldata", "STASHmaster", "STASHmaster_A")
            return cls.from_file(filename)
        else:
            msg = ("Unable to load STASHmaster from version string; UMDIR "
                   "environment variable not set")
            warnings.warn(msg)
            return None

    @classmethod
    def from_umfile(cls, umfile):
        """
        Load the STASHmaster from a :class:`mule.UMFile` object.

        Args:
            * umfile:
                A UM file object; the version will be extracted from
                its fixed length header and used to try and load the
                correct STASHmaster file.

        """
        um_int_version = umfile.fixed_length_header.model_version
        if um_int_version != umfile.fixed_length_header.MDI:
            um_version = "{0}.{1}".format(um_int_version // 100,
                                          um_int_version % 10)
            return cls.from_version(um_version)
        else:
            msg = ("Fixed length header does not define the UM model "
                   "version number, unable to load STASHmaster file")
            warnings.warn(msg)
            return None

    def by_section(self, section):
        """
        Return a new :class:`STASHmaster` which contains a subset of the
        original object, selected by section code.

        Args:
           * section:
               The section code which should be contained in the subset.

        """
        subset = STASHmaster()
        for key, val in self.items():
            if val.section == section:
                subset[key] = val
        return subset

    def by_item(self, item):
        """
        Return a new :class:`STASHmaster` which contains a subset of the
        original object, selected by item code.

        Args:
           * item:
               The item code which should be contained in the subset.

        """
        subset = STASHmaster()
        for key, val in self.items():
            if val.item == item:
                subset[key] = val
        return subset

    def by_regex(self, regex):
        """
        Return a new :class:`STASHmaster` which contains a subset of the
        original object, selected by a regex applied to the "name" property.

        Args:
           * name:
               The regex to use to search in the name property.

        """
        subset = STASHmaster()
        for key, val in self.items():
            if re.search(regex, val.name, flags=re.IGNORECASE):
                subset[key] = val
        return subset

    def __repr__(self):
        return ("<stashmaster.STASHmaster object: {0:d} entries>"
                .format(len(self)))

    def __str__(self):
        return "\n".join([str(self[key]) for key in sorted(self.keys())])

    def _key_process(self, key):
        """
        Custom processor for dictionary keys - this allows the key to be
        any type which will convert to an integer.

        """
        try:
            key = "{0:05d}".format(int(key))
        except ValueError:
            raise STASHLookupError("STASH code must be convertible to digit")
        return key

    def __getitem__(self, key):
        """Overrides parent dict method to apply cutom key processor."""
        key = self._key_process(key)
        return super(STASHmaster, self).__getitem__(key)

    def __setitem__(self, key, val):
        """
        Overrides parent dict method to apply custom key processor, and
        also ensures only :class:`STASHentry` objects can be used as values.

        """
        key = self._key_process(key)
        if type(val) is not STASHentry:
            raise STASHLookupError("Value must be a STASHentry object")
        return super(STASHmaster, self).__setitem__(key, val)

    def has_key(self, key):
        """Overrides parent dict method to apply cutom key processor."""
        key = self._key_process(key)
        return super(STASHmaster, self).has_key(key)

    def __contains__(self, key):
        """Overrides parent dict method to apply cutom key processor."""
        key = self._key_process(key)
        return super(STASHmaster, self).__contains__(key)
