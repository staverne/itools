# -*- coding: UTF-8 -*-
# Copyright (C) 2005-2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
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
import warnings

# Import from itools
from itools.datatypes import String, Unicode
from itools.schemas import BaseSchema, register_schema
from parser import XMLError



"""
This module keeps a registry for namespaces and namespace handlers.

Namespace handlers are used through the parsing process, they are
responsible to deal with the elements and attributes associated to
them.

This module provides an API to register namespace uris and handlers,
and to ask this registry.

It also provides a registry from namespace prefixes to namespace uris.
While namespace prefixes are local to an XML document, it is sometimes
useful to refer to a namespace through its prefix. This feature must
be used carefully, collisions
"""


#############################################################################
# The registry
#############################################################################

namespaces = {}
prefixes = {}


def set_namespace(namespace):
    """
    Associates a namespace handler to a namespace uri. It a prefix is
    given it also associates that that prefix to the given namespace.
    """
    namespaces[namespace.class_uri] = namespace

    prefix = namespace.class_prefix
    if prefix is not None:
        if prefix in prefixes:
            warnings.warn('The prefix "%s" is already registered.' % prefix)
        prefixes[prefix] = namespace.class_uri


def get_namespace(namespace_uri):
    """
    Returns the namespace handler associated to the given uri. If there
    is none the default namespace handler will be returned, and a warning
    message will be issued.
    """
    if namespace_uri in namespaces:
        return namespaces[namespace_uri]

    # Use default
    warnings.warn('Unknown namespace "%s" (using default)' % namespace_uri)
    return namespaces[None]


def has_namespace(namespace_uri):
    """
    Returns true if there is namespace handler associated to the given uri.
    """
    return namespace_uri in namespaces


def get_namespace_by_prefix(prefix):
    """
    Returns the namespace handler associated to the given prefix. If there
    is none the default namespace handler is returned, and a warning message
    is issued.
    """
    if prefix in prefixes:
        namespace_uri = prefixes[prefix]
        return get_namespace(namespace_uri)

    # Use default
    warnings.warn('Unknown namespace prefix "%s" (using default)' % prefix)
    return namespaces[None]


def get_element_schema(namespace, name):
    return get_namespace(namespace).get_element_schema(name)


def is_empty(namespace, name):
    schema = get_namespace(namespace).get_element_schema(name)
    return schema.get('is_empty', False)


#############################################################################
# Namespaces
#############################################################################

class AbstractNamespace(object):
    """
    This class defines the default behaviour for namespaces, which is to
    raise an error.

    Subclasses should define:

    class_uri
    - The uri that uniquely identifies the namespace.

    class_prefix
    - The recommended prefix.

    get_element_schema(name)
    - Returns a dictionary that defines the schema for the given element.
    """

    class_uri = None
    class_prefix = None


    @staticmethod
    def get_element_schema(name):
        raise XMLError, 'undefined element "%s"' % name


    #######################################################################
    # Internationalization
    @classmethod
    def is_translatable(cls, tag_uri, tag_name, attributes, attribute_name):
        """
        Some elements may contain text addressed to users, that is, text
        that could be translated in different human languages, for example
        the 'p' element of XHTML. This method should return 'True' in that
        cases, False (the default) otherwise.

        If the parameter 'attribute_name' is given, then we are being asked
        wether that attribute is or not translatable. An example is the 'alt'
        attribute of the 'img' elements of XHTML.
        """
        return False



class DefaultNamespace(AbstractNamespace):
    """
    Default namespace handler for elements and attributes that are not bound
    to a particular namespace.
    """

    class_uri = None
    class_prefix = None


    @staticmethod
    def get_element_schema(name):
        return {'is_empty': False}



class XMLNamespace(AbstractNamespace, BaseSchema):

    class_uri = 'http://www.w3.org/XML/1998/namespace'
    class_prefix = 'xml'


    @staticmethod
    def get_datatype(name):
        if name == 'lang':
            return String
        return Unicode



class XMLNSNamespace(AbstractNamespace, BaseSchema):

    class_uri = 'http://www.w3.org/2000/xmlns/'
    class_prefix = 'xmlns'


    @staticmethod
    def get_datatype(name):
        return String



# Register the namespaces
set_namespace(DefaultNamespace)
register_schema(XMLNamespace)
register_schema(XMLNSNamespace)
set_namespace(XMLNamespace)
set_namespace(XMLNSNamespace)
