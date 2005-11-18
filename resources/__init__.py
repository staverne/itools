# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2003-2005 Juan David Ib��ez Palomar <jdavid@itaapy.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA


# Import from Python
import os
from urlparse import urlsplit

# Import from itools
from itools import uri
import file
import http


def get_resource(reference):
    """
    From a uri reference returns a resource. Supported schemes:

    - file (the default)

    - http (only file resources, no language negotiation)
    """
    if not isinstance(reference, uri.generic.Reference):
        reference = uri.get_reference(reference)

    base = os.getcwd()
    # Make it working with Windows. Internally we use always the "/".
    if os.path.sep == '\\':
        base = base.replace(os.path.sep, '/')

    base = uri.generic.decode('file://%s/' % base)
    reference = base.resolve(reference)

    scheme = reference.scheme

    if scheme == 'file':
        # reference must be a path
        return file.get_resource(reference)
    elif scheme == 'http':
        return http.get_resource(reference)

    raise ValueError, 'scheme "%s" unsupported' % scheme
