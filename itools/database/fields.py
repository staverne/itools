# -*- coding: UTF-8 -*-
# Copyright (C) 2011-2012 J. David Ibáñez <jdavid.ibp@gmail.com>
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

# Import from itools
from itools.core import is_prototype, prototype, prototype_type
from itools.gettext import MSG


fields_index = {}

def register_field_in_index(cls):
    fields_index[cls.field_id] = cls


def get_field_from_index(field_id):
    return fields_index[field_id]


class BaseFieldMetaclass(prototype_type):

    def __new__(mcs, name, bases, dict):
        cls = prototype_type.__new__(mcs, name, bases, dict)
        if 'field_id' in dict and cls.field_id:
            register_field_in_index(cls)
        return cls


class field_prototype(prototype):

    __metaclass__ = BaseFieldMetaclass



class Field(field_prototype):

    field_id = None
    name = None
    title = None
    datatype = None
    indexed = False
    stored = False
    multiple = False
    error_messages = {
        'invalid': MSG(u'Invalid value.'),
        'required': MSG(u'This field is required.'),
    }

    def get_datatype(self):
        return self.datatype


    def access(self, mode, resource):
        # mode may be "read" or "write"
        return True



def get_field_and_datatype(elt):
    """ Now schema can be Datatype or Field.
    To be compatible:
      - we return datatype if a field is given
      - we build a field if a datatype is given

    """
    if is_prototype(elt, Field):
        return elt, elt.get_datatype()
    return Field(datatype=elt), elt
