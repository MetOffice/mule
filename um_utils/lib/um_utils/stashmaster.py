#!/usr/bin/env python
# *****************************COPYRIGHT******************************
# (C) Crown copyright Met Office. All rights reserved.
# For further details please refer to the file LICENCE.txt
# which you should have received as part of this distribution.
# *****************************COPYRIGHT******************************
"""
This module provides the means to load and interact with the entries in a UM
STASHmaster file

"""
import os
import re

# Exception handlers
class IncompleteEnvironmentError(Exception):
    """
    Exception used when a required environment variable which should be 
    present by default is missing.
    
    """
    def __init__(self, var):
        self.var = var
    def __repr__(self):
        return ("Incomplete environment - "
                "variable {0:s} is not set".format(self.var))

class STASHLookupError(Exception):
    """
    Exception used when a STASH code lookup has failed.
    
    """
    def __init__(self, msg):
        self.msg = msg
    def __repr__(self):
        return "STASH lookup error - {0:s}".format(self.msg)

class STASHParseError(Exception):
    """
    Exception used when parsing the STASHmaster has failed.
    
    """
    def __init__(self, msg):
        self.msg = msg
    def __repr__(self):
        return "STASH parsing error - {0:s}".format(self.msg)    

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
_PACKING_CODE_NAMES = [ "PC{0:d}".format(i+1) for i in range(9) ] + ["PCA"]
_OPTION_CODE_NAMES = [ "n{0:d}".format(i+1) for i in range(30) ]

class _STASHentry(object):
    """
    Object which stores a single STASHmaster record, with each field assigned
    as an attribute using the names defined in _STASH_ENTRY_NAMES.
    
    """
    def __init__(self, entries):
        if len(entries) != len(_STASH_ENTRY_NAMES):
            raise STASHParseError("Error parsing STASHmaster (corrupt record)")
        for i, name in enumerate(_STASH_ENTRY_NAMES):
            if name == "packing_codes":
                entry = dict(zip(
                    _PACKING_CODE_NAMES, map(int, entries[i].split())))
            elif name == "option_codes":
                entry = dict(zip(
                    _OPTION_CODE_NAMES, map(int, entries[i][::-1])))
            else:
                if entries[i].isdigit():
                    entry = int(entries[i])
                else:
                    entry = entries[i]
            setattr(self, name, entry)
            
    def __repr__(self):
        return ("<stashmaster._STASHentry object: "
                "SC:{0:5d} - \"{1:s}\">".format(
                    (1000*self.section + self.item), self.name))
    
    
class STASHmaster(dict):
    """
    Class to represent a STASHmaster file. Construction takes an optional
    argument which is the STASHmaster file to use. If this is missing, it will
    take a best guess based on your environment. The resulting object behaves
    like a python dictionary with some restrictions (keys must be integers or
    digits as strings, values must be _STASHentry objects).
    
    """

    def __init__(self, fname=None, empty=False, version=None):
        """
        Initialise the STASHmaster object.

        Kwargs:

        * fname:
            The direct path to a valid STASHmaster file, if not supplied the
            environment will be searched for a default UM install location i.e.
            $UMDIR/vn$VN/ctldata/STASHmaster/STASHmaster_A  (the relevant
            environment variables UMDIR and VN must be set).

        * empty:
            Used to initialise a new object without parsing an existing file
            (this is mainly used by methods which return a subset of the full
            STASHmaster).

        * version:
            Used to provide the UM version, if relying on the resolution of the
            UMDIR and VN environment variables (see above) but wishing to force
            the loading of a different STASHmaster version.  Must be a string
            e.g. "vn10.2".

        """
        if empty:
            return
        
        if fname and os.path.isfile(fname):
            self.stashmaster = fname
        else:
            version = self._ascertain_version(version)
            if 'UMDIR' not in os.environ:
                raise IncompleteEnvironmentError('UMDIR')
            umdir = os.environ['UMDIR']
            self.stashmaster = os.path.join(umdir, version, 'ctldata', 
                'STASHmaster', 'STASHmaster_A')
        if hasattr(self, 'stashmaster'):
            self._load_stashmaster()             

    def __repr__(self):
        return "<stashmaster.STASHmaster object: {0:d} entries>".format(len(self))

    def __str__(self):
        return "\n".join([str(self[key]) for key in sorted(self.keys())])

    def _key_process(self, key):
        try:
            key = "{0:05d}".format(int(key))
        except ValueError:
            raise STASHLookupError("STASH code must convert to digit")
        return key

    def __getitem__(self, key):
        key = self._key_process(key)
        return super(STASHmaster, self).__getitem__(key)

    def __setitem__(self, key, val):
        key = self._key_process(key)
        if type(val) is not _STASHentry:
            raise STASHLookupError("Value must be a _STASHentry object")
        return super(STASHmaster, self).__setitem__(key, val)

    def _read_file(self, fname):
        """Return contents of a file given filename."""
        with open(fname, 'r') as fh:
            lines = fh.read()
        return lines

    def _ascertain_version(self, version):
        """Work out UM version from environment it wasn't provided."""
        if version is not None:
            return version
        elif 'VN' in os.environ:
            return "vn{0:s}".format(os.environ['VN'])
        else:
            raise IncompleteEnvironmentError("VN")

    def _load_stashmaster(self):
        """Load the STASHmaster for a given version."""
        lines = self._read_file(self.stashmaster)

        entries = re.findall(r"^1\s*\|(.*)\n"
                             r"2\s*\|(.*)\n"
                             r"3\s*\|(.*)\n"
                             r"4\s*\|(.*)\n"
                             r"5\s*\|(.*)\|\s*$",
                             lines, flags=re.MULTILINE)

        for entry in entries:
            entry_obj = _STASHentry(map(str.strip, "".join(entry).split("|")))
            if entry_obj.name == "END OF FILE MARK":
                continue
            stashcode = "{0:02d}{1:03d}".format(int(entry_obj.section),
                                                int(entry_obj.item))
            self[stashcode] = entry_obj

    def has_key(self, key):
        key = self._key_process(key)
        return super(STASHmaster, self).has_key(key)

    def by_regex(self, regex):
        subset = STASHmaster(empty=True)
        for key, val in self.items():
            if re.search(regex, val.name, flags=re.IGNORECASE):
                subset[key] = val
        if len(subset) == 1:
            return subset.values()[0]
        else:
            return subset

    def by_section(self, sec):
        subset = STASHmaster(empty=True)
        for key, val in self.items():
            if val.section == sec:
                subset[key] = val
        if len(subset) == 1:
            return subset.values()[0]
        else:
            return subset                

    def by_item(self, item):
        subset = STASHmaster(empty=True)
        for key, val in self.items():
            if val.item == item:
                subset[key] = val
        if len(subset) == 1:
            return subset.values()[0]
        else:
            return subset                                
                
if __name__ == "__main__":
    print "Testing read of STASHmaster"
    import sys
    if len(sys.argv) > 1:
        sm = STASHmaster(sys.argv[1])
    else:
        sm = STASHmaster()    
    print sm.__repr__()
