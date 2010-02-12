# -*- coding: UTF-8 -*-
# Copyright (C) 2003-2008 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2007 Henry Obein <henry@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the Standard Library
from copy import deepcopy
from cStringIO import StringIO
from datetime import datetime

# Import from itools
from itools.vfs import vfs
from registry import register_handler_class
from base import Handler



class File(Handler):
    """This is the base handler class for any file handler. It is also used
    as the default handler class for any file resource that has not a more
    specific handler.

    The variables 'timestamp' and 'dirty' define the state of the file
    handler:

       timestamp/dirty => means...
       -------------------------------------
       None/None => not loaded (yet)
       None/<dt> => new
       <dt>/None => loaded, but not changed
       <dt>/<dt> => loaded, and changed

    """

    # By default handlers are not loaded
    timestamp = None
    dirty = None


    def __init__(self, ref=None, string=None, **kw):
        if ref is None:
            self.reset()
            self.dirty = datetime.now()
            if string is not None:
                # A handler from a byte string
                self.load_state_from_string(string)
            else:
                # A handler from some input data
                self.new(**kw)
        else:
            self.uri = vfs.get_uri(ref)


    def reset(self):
        pass


    def new(self, data=''):
        self.data = data


    def __getattr__(self, name):
        # Not attached to a URI or already loaded (should be correctly
        # initialized)
        if self.uri is None or self.timestamp is not None:
            message = "'%s' object has no attribute '%s'"
            raise AttributeError, message % (self.__class__.__name__, name)

        # Load and try again
        self.load_state()
        return getattr(self, name)


    #########################################################################
    # Load / Save
    #########################################################################
    def _load_state_from_file(self, file):
        """Method to be overriden by sub-classes."""
        self.data = file.read()


    def load_state(self):
        file = vfs.open(self.uri)
        self.reset()
        try:
            self._load_state_from_file(file)
        except Exception:
            self._clean_state()
            raise
        finally:
            file.close()

        self.timestamp = vfs.get_mtime(self.uri)
        self.dirty = None


    def load_state_from(self, uri):
        file = vfs.open(uri)
        try:
            self.load_state_from_file(file)
        finally:
            file.close()


    def load_state_from_file(self, file):
        self.set_changed()
        self.reset()
        try:
            self._load_state_from_file(file)
        except Exception:
            self._clean_state()
            raise


    def load_state_from_string(self, string):
        file = StringIO(string)
        self.load_state_from_file(file)


    def save_state(self):
        file = self.safe_open(self.uri, 'w')
        try:
            self.save_state_to_file(file)
        finally:
            file.close()
        # Update the timestamp
        self.timestamp = vfs.get_mtime(self.uri)
        self.dirty = None


    def save_state_to(self, uri):
        # If there is an empty folder in the given URI, remove it
        if vfs.is_folder(uri) and not vfs.get_names(uri):
            vfs.remove(uri)
        # Save the file
        file = self.safe_make_file(uri)
        try:
            self.save_state_to_file(file)
        finally:
            file.close()


    def save_state_to_file(self, file):
        # We call "to_str" so this method will be good for sub-classes
        data = self.to_str()
        # Write and truncate (calls to "_save_state" must be done with the
        # pointer pointing to the beginning)
        file.write(data)
        file.truncate(file.tell())


    clone_exclude = frozenset(['database', 'uri', 'timestamp', 'dirty'])
    def clone(self, cls=None):
        # Define the class to build
        if cls is None:
            cls = self.__class__
        elif not issubclass(cls, self.__class__):
            msg = 'the given class must be a subclass of the object'
            raise ValueError, msg

        # Load first, if needed
        if self.dirty is None:
            if self.uri is not None and self.timestamp is None:
                self.load_state()

        # Copy the state
        copy = object.__new__(cls)
        copy.reset()
        for name in self.__dict__:
            if name not in cls.clone_exclude:
                value = getattr(self, name)
                value = deepcopy(value)
                setattr(copy, name, value)
        copy.dirty = datetime.now()
        return copy


    def is_outdated(self):
        if self.uri is None:
            return False

        timestamp = self.timestamp
        # It cannot be out-of-date if it has not been loaded yet
        if timestamp is None:
            return False

        mtime = vfs.get_mtime(self.uri)
        # If the resource layer does not support mtime... we are...
        if mtime is None:
            return True

        return mtime > timestamp


    def set_changed(self):
        # Invalid handler
        if self.uri is None and self.dirty is None:
            raise RuntimeError, 'cannot change an orphaned file handler'

        # Free handler (not attached to a database)
        if self.database is None:
            self.dirty = datetime.now()
            return

        # Phantoms
        database = self.database
        if database.is_phantom(self):
            database.cache[self.uri] = self
            database.added.add(self.uri)
            return

        # Check nothing weird happened
        if self.uri is None or database.cache.get(self.uri) is not self:
            raise RuntimeError, 'database inconsistency!'

        # Update database state
        if self.timestamp:
            # Case 1: loaded
            self.dirty = datetime.now()
            database.changed.add(self.uri)
        elif self.dirty:
            # Case 2: new
            database.added.add(self.uri)
        else:
            # Case 3: not loaded (yet)
            self.load_state()
            self.dirty = datetime.now()
            database.changed.add(self.uri)


    def _clean_state(self):
        names = [ x for x in self.__dict__ if x not in ('database', 'uri') ]
        for name in names:
            delattr(self, name)


    def abort_changes(self):
        # Not attached to a URI or not changed
        if self.uri is None or self.dirty is None:
            return
        # Abort
        self._clean_state()


    #########################################################################
    # API
    #########################################################################
    def get_mtime(self):
        """Returns the last modification time.
        """
        # Modified or new handler
        if self.dirty is not None:
            return self.dirty

        # Loaded but not modified
        if self.timestamp is not None:
            return self.timestamp

        # Not yet loaded, check the VFS
        return vfs.get_mtime(self.uri)


    def to_str(self):
        return self.data


    def set_data(self, data):
        self.set_changed()
        self.data = data


    def to_text(self):
        raise NotImplementedError


    def is_empty(self):
        raise NotImplementedError



register_handler_class(File)
