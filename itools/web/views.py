# -*- coding: UTF-8 -*-
# Copyright (C) 2008 Gautier Hayoun <gautier.hayoun@supinfo.com>
# Copyright (C) 2008 Nicolas Deram <nderam@gmail.com>
# Copyright (C) 2008, 2011 Henry Obein <henry.obein@gmail.com>
# Copyright (C) 2008-2009 Hervé Cauwelier <herve@oursours.net>
# Copyright (C) 2008-2011 J. David Ibáñez <jdavid.ibp@gmail.com>
# Copyright (C) 2011 David Versmisse <versmisse@lil.univ-littoral.fr>
# Copyright (C) 2012 Sylvain Taverne <taverne.sylvain@gmail.com>
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
from json import dumps

# Import from itools
from itools.core import freeze, prototype
from itools.database import ReadonlyError, get_field_and_datatype
from itools.datatypes import Enumerate, String
from itools.gettext import MSG
from itools.handlers import File
from itools.stl import stl
from itools.uri import decode_query, Reference

# Import from here
from exceptions import FormError
from messages import ERROR
from utils import NewJSONEncoder



def process_form(get_value, schema, error_msg=None):
    missings = []
    invalids = []
    unknow = []
    values = {}
    for name in schema:
        datatype = schema[name]
        try:
            values[name] = get_value(name, type=datatype)
        except FormError, e:
            if e.missing:
                missings.append(name)
            elif e.invalid:
                invalids.append(name)
            else:
                unknow.append(name)
    if missings or invalids or unknow:
        error_msg = error_msg or ERROR(u'Form values are invalid')
        raise FormError(
            message=error_msg,
            missing=len(missings)>0,
            invalid=len(invalids)>0,
            missings=missings,
            invalids=invalids)
    return values



class BaseView(prototype):

    # Access Control
    access = False

    def __init__(self, **kw):
        for key in kw:
            setattr(self, key, kw[key])


    #######################################################################
    # GET
    #######################################################################
    def GET(self, resource, context):
        raise NotImplementedError


    #######################################################################
    # Query
    query_schema = {}


    def get_query_schema(self):
        return self.query_schema


    def get_query(self, context):
        get_value = context.get_query_value
        schema = self.get_query_schema()
        return process_form(get_value, schema)


    #######################################################################
    # Caching
    def get_mtime(self, resource):
        return None


    #######################################################################
    # View's metadata
    title = None

    def get_title(self, context):
        return self.title


    #######################################################################
    # Canonical URI for search engines
    # "language" is by default because too widespreaded
    canonical_query_parameters = freeze(['language'])


    def get_canonical_uri(self, context):
        """Return the same URI stripped from redundant view name, if already
        the default, and query parameters not affecting the resource
        representation.
        Search engines will keep this sole URI when crawling different
        combinations of this view.
        """
        uri = deepcopy(context.uri)
        query = uri.query

        # Remove the view name if default
        name = uri.path.get_name()
        view_name = name[1:] if name and name[0] == ';' else None
        if view_name:
            resource = context.resource
            if view_name == resource.get_default_view_name():
                uri = uri.resolve2('..')
                view_name = None

        # Be sure the canonical URL either has a view or ends by an slash
        if not view_name and uri.path != '/':
            uri.path.endswith_slash = True

        # Remove noise from query parameters
        canonical_query_parameters = self.canonical_query_parameters
        for parameter in query.keys():
            if parameter not in canonical_query_parameters:
                del query[parameter]
        uri.query = query

        # Ok
        return uri


    #######################################################################
    # POST
    #######################################################################
    schema = {}


    def get_schema(self, resource, context):
        # Check for specific schema
        action = getattr(context, 'form_action', None)
        if action is not None:
            schema = getattr(self, '%s_schema' % action, None)
            if schema is not None:
                return schema

        # Default
        return self.schema


    form_error_message = ERROR(u'There are errors, check below')
    def _get_form(self, resource, context):
        """Form checks the request form and collect inputs consider the
        schema.  This method also checks the request form and raise an
        FormError if there is something wrong (a mandatory field is missing,
        or a value is not valid) or None if everything is ok.

        Its input data is a list (fields) that defines the form variables to
          {'toto': Unicode(mandatory=True, multiple=False, default=u'toto'),
           'tata': Unicode(mandatory=True, multiple=False, default=u'tata')}
        """
        get_value = context.get_form_value
        schema = self.get_schema(resource, context)
        return process_form(get_value, schema, self.form_error_message)


    def get_value(self, resource, context, name, datatype):
        return datatype.get_default()


    def get_action(self, resource, context):
        """Default function to retrieve the name of the action from a form
        """
        # 1. Get the action name
        form = context.get_form()
        action = form.get('action')
        action = ('action_%s' % action) if action else 'action'

        # 2. Check whether the action has a query
        if '?' in action:
            action, query = action.split('?')
            # Deserialize query using action specific schema
            schema = getattr(self, '%s_query_schema' % action, None)
            context.form_query = decode_query(query, schema)

        # 3. Save the action name (used by get_schema)
        context.form_action = action

        # 4. Return the method
        return getattr(self, action, None)


    def on_form_error(self, resource, context):
        content_type, type_parameters = context.get_header('content-type')
        if content_type == 'application/json':
            return self.on_form_error_json(resource, context)
        return self.on_form_error_default(resource, context)


    def on_form_error_default(self, resource, context):
        context.message = context.form_error.get_message()
        # Return to GET view on error
        return self.GET


    def on_form_error_json(self, resource, context):
        error = context.form_error
        error_kw = error.to_dict()
        return self.return_json(error_kw, context)


    def on_query_error(self, resource, context):
        accept = context.get_header('accept')
        if accept == 'application/json':
            return self.on_query_error_json(resource, context)
        return self.on_query_error_default(resource, context)


    def on_query_error_default(self, resource, context):
        message = MSG(u'The query could not be processed.').gettext()
        return message.encode('utf-8')


    def on_query_error_json(self, resource, context):
        error = context.form_error
        error_kw = error.to_dict()
        return self.return_json(error_kw, context)


    def return_json(self, data, context):
        context.set_content_type('application/json')
        return dumps(data, cls=NewJSONEncoder)


    def POST(self, resource, context):
        # (1) Find out which button has been pressed, if more than one
        method = self.get_action(resource, context)
        if method is None:
            msg = "POST method not supported because no '%s' defined"
            raise NotImplementedError, msg % context.form_action

        # (2) Automatically validate and get the form input (from the schema).
        try:
            form = self._get_form(resource, context)
        except FormError, error:
            context.form_error = error
            return self.on_form_error(resource, context)

        # (3) Action
        try:
            goto = method(resource, context, form)
        except ReadonlyError:
            context.message = ERROR('This website is under maintenance. '
                                    'Please try again later.')
            return self.GET

        # (4) Return
        if goto is None:
            return self.GET
        return goto


    #######################################################################
    # PUT
    #######################################################################
    def PUT(self, resource, context):
        # Check content-range
        range = context.get_header('content-range')
        if range:
            raise NotImplemented
        # Check if handler is a File
        handler = resource.get_value('data')
        if not isinstance(handler, File):
            raise ValueError, u"PUT only allowed on files"
        # Save the data
        body = context.get_form_value('body')
        handler.load_state_from_string(body)
        context.database.change_resource(resource)



class STLView(BaseView):

    template = None


    def get_template(self, resource, context):
        # Check there is a template defined
        template = self.template
        if template is None:
            msg = "%s is missing the 'template' variable"
            raise NotImplementedError, msg % repr(self.__class__)

        # Case 1: a path to a file somewhere
        template_type = type(template)
        if template_type is str:
            template = context.get_template(template)
            if template is None:
                msg = 'Template "{0}" was not found'
                raise ValueError(msg.format(self.template))
            return template

        # Case 2: the stream ready to use
        if template_type is list:
            return template

        # Error
        error = 'unexpected type "%s" for the template' % template_type
        raise TypeError, error


    def GET(self, resource, context):
        # Get the namespace
        namespace = self.get_namespace(resource, context)
        if isinstance(namespace, Reference):
            return namespace

        # STL
        template = self.get_template(resource, context)
        if type(template) is list:
            return stl(None, namespace, events=template)

        return stl(template, namespace)


    #######################################################################
    # POST
    #######################################################################
    def get_namespace(self, resource, context, query=None):
        """This utility method builds a namespace suitable to use to produce
        an HTML form. Its input data is a dictionnary that defines the form
        variables to consider:

          {'toto': Unicode(mandatory=True, multiple=False, default=u'toto'),
           'tata': Unicode(mandatory=True, multiple=False, default=u'tata')}

        Every element specifies the datatype of the field.
        The output is like:

            {<field name>: {'value': <field value>, 'class': <CSS class>}
             ...}
        """
        # Figure out whether the form has been submit or not (FIXME This
        # heuristic is not reliable)
        schema = self.get_schema(resource, context)
        submit = (context.method == 'POST')

        # Build the namespace
        namespace = {}
        for name in schema:
            elt = schema[name]
            field, datatype = get_field_and_datatype(elt)
            is_readonly = getattr(datatype, 'readonly', False)
            is_multilingual = getattr(datatype, 'multilingual', False)

            error = None
            if submit and not is_readonly:
                try:
                    value = context.get_form_value(name, type=field)
                except FormError, err:
                    error = err.get_message()
                    if issubclass(datatype, Enumerate):
                        value = datatype.get_namespace(None)
                    else:
                        generic_datatype = String(multilingual=is_multilingual)
                        value = context.get_form_value(name,
                                                       type=generic_datatype)
                else:
                    if issubclass(datatype, Enumerate):
                        value = datatype.get_namespace(value)
                    elif is_multilingual:
                        for language in value:
                            value[language] = datatype.encode(value[language])
                    else:
                        value = datatype.encode(value)
            else:
                try:
                    value = self.get_value(resource, context, name, datatype)
                except FormError, err:
                    error = err.get_message()
                    if issubclass(datatype, Enumerate):
                        value = datatype.get_namespace(None)
                    else:
                        value = None
                else:
                    if issubclass(datatype, Enumerate):
                        value = datatype.get_namespace(value)
                    elif is_multilingual:
                        for language in value:
                            value[language] = datatype.encode(value[language])
                    else:
                        value = datatype.encode(value)
            namespace[name] = {'name': name, 'value': value, 'error': error}
        return namespace
