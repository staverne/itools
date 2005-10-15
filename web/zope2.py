# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2005 Juan David Ib��ez Palomar <jdavid@itaapy.com>
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307  USA

# Import from the Standard Library
import cStringIO

# Import from itools
from itools import uri
from itools.resources import memory
from itools.i18n.accept import AcceptCharset, AcceptLanguage
from itools.web.context import Context, set_context
from itools.web.request import Request
from itools.web.entities import Entity


def init(zope_request):
    environ = zope_request.environ

    # Build the request
    request = Request()

    # The request method
    request_method = environ['REQUEST_METHOD']
    request.set_method(request_method)

    # The query
    query = zope_request.environ.get('QUERY_STRING', '')
    query = uri.generic.Query(query)

    # The path
    if 'REAL_PATH' in query:
        path = query.pop('REAL_PATH')
    else:
        path = zope_request.environ['PATH_INFO']
    request.set_path(path)

    # The header
    for name, key in [('Referer', 'HTTP_REFERER'),
                      ('Content-Type', 'CONTENT_TYPE')]:
        if environ.has_key(key):
            value = environ[key]
            request.set_header(name, value)

    # The form
    if request_method in ('GET', 'HEAD'):
        parameters = query
    else:
        # Read the standard input
        body = zope_request.stdin.read()
        # Recover the standard input, so Zope can read it again
        zope_request.stdin = cStringIO.StringIO(body)
        # Load the parameters
        type, type_parameters = request.content_type
        if type == 'application/x-www-form-urlencoded':
            parameters = uri.generic.Query(body)
        elif type.startswith('multipart/'):
            boundary = type_parameters.get('boundary')
            boundary = '--%s' % boundary
            parameters = {}
            for part in body.split(boundary)[1:-1]:
                if part.startswith('\r\n'):
                    part = part[2:]
                elif part.startswith('\n'):
                    part = part[1:]
                # Parse the entity
                resource = memory.File(part)
                entity = Entity(resource)
                # Find out the parameter name
                header = entity.get_header('Content-Disposition')
                value, header_parameters = header
                name = header_parameters['name']
                # Load the value
                body = entity.get_body()
                if body.endswith('\r\n'):
                    body = body[:-2]
                elif body.endswih('\n'):
                    body = body[:-1]
                if 'filename' in header_parameters:
                    filename = header_parameters['filename']
                    if filename:
                        # Strip the path (for IE). XXX Test this.
                        filename = filename.split('\\')[-1]
                        resource = memory.File(body, name=filename)
                        parameters[name] = resource
                else:
                    parameters[name] = body
        else:
            raise ValueError, \
                  'content type "%s" not yet implemented' % content_type

    for name in parameters:
        value = parameters[name]
        request.set_parameter(name, value)

    # The cookies
    request.state.cookies = zope_request.cookies

    # Build the context
    context = Context(request)
    set_context(context)

    # The authority
    if 'HTTP_X_FORWARDED_HOST' in environ:
        authority = environ['HTTP_X_FORWARDED_HOST']
    else:
        authority = zope_request['HTTP_HOST']

    # The URI
    request_uri = 'http://%s/%s?%s' % (authority, path, query)
    context.uri = uri.get_reference(request_uri)

    # Accept charset
    accept_charset = environ.get('HTTP_ACCEPT_CHARSET', '')
    accept_charset = AcceptCharset(accept_charset)

    # Accept language
    accept_language = environ.get('HTTP_ACCEPT_LANGUAGE', '')

    # Patches for user agents that don't support correctly the protocol
    user_agent = environ['HTTP_USER_AGENT']
    if user_agent.startswith('Mozilla/4') and user_agent.find('MSIE') == -1:
        # Netscape 4.x
        q = 1.0
        langs = []
        for lang in [ x.strip() for x in accept_language.split(',') ]:
            langs.append('%s;q=%f' % (lang, q))
            q = q/2
        accept_language = ','.join(langs)

    accept_language = AcceptLanguage(accept_language)
    request.accept_language = accept_language

