# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Hervé Cauwelier <herve@itaapy.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA

# Import from the future
from __future__ import absolute_import
from __future__ import with_statement

# Import from the Standard Library
import re
from operator import itemgetter
from tempfile import mkdtemp
from subprocess import call

# Import from itools
from .. import uri
from .. import vfs
from ..web import get_context
from ..stl import stl
from ..datatypes import Unicode, FileName

# Import from itools.cms
from .File import File
from .Folder import Folder
from .text import Text
from .registry import register_object_class
from .utils import checkid
from .widgets import table

# Import from docutils
try:
    import docutils
except ImportError:
    print "docutils is not installed, wiki deactivated."
    raise
from docutils import core
from docutils import io
from docutils import readers
from docutils import nodes


class WikiFolder(Folder):
    class_id = 'WikiFolder'
    class_version = '20061229'
    class_title = u"Wiki Folder"
    class_description = u"Container for a wiki"
    class_icon16 = 'images/WikiFolder16.png'
    class_icon48 = 'images/WikiFolder48.png'
    class_views = [
        ['view'],
        ['browse_content?mode=thumbnails',
         'browse_content?mode=list',
         'browse_content?mode=image'],
        ['new_resource_form'],
        ['edit_metadata_form'],
        ['last_changes']]

    __fixed_handlers__ = ['FrontPage']


    def new(self, **kw):
        Folder.new(self, **kw)
        cache = self.cache
        page = WikiPage()
        cache['FrontPage'] = page
        cache['FrontPage.metadata'] = self.build_metadata(page,
                **{'dc:title': {'en': u"Front Page"}})


    def get_document_types(self):
        return [WikiPage, File]


    def before_set_handler(self, segment, handler, format=None, id=None,
                           move=False, **kw):
        Folder.before_set_handler(self, segment, handler, format, id,
                                  move, **kw)
        if isinstance(handler, WikiPage):
            context = get_context()
            if context is not None:
                data = context.get_form_value('data', default='')
                handler.load_state_from_string(data)


    #######################################################################
    # User interface
    #######################################################################
    def GET(self, context):
        if context.has_form_value('message'):
            message = context.get_form_value('message')
            return context.come_back(message, 'FrontPage')
        return context.uri.resolve2('FrontPage')


    view__access__ = 'is_allowed_to_view'
    view__label__ = u"View"
    def view(self, context):
        if context.has_form_value('message'):
            message = context.get_form_value('message')
            return context.come_back(message, 'FrontPage')
        return context.uri.resolve('FrontPage')



    last_changes__access__ = 'is_allowed_to_view'
    last_changes__label__ = u"Last Changes"
    def last_changes(self, context, sortby=['mtime'], sortorder='down'):
        users = self.get_handler('/users')
        namespace = {}
        pages = []

        namespace['search_fields'] = None
        namespace['batch'] = ''

        for page in self.search_handlers(handler_class=WikiPage):
            revisions = page.get_revisions(context)
            if revisions:
                last_rev = revisions[0]
                username = last_rev['username']
                try:
                    user = users.get_handler(username)
                    user_title = user.get_title()
                    if not user_title.strip():
                        user_title = user.get_property('ikaaro:email')
                except LookupError:
                    user_title = username
            else:
                user_title = '?'
            pages.append({'name': (page.name, page.name),
                          'title': page.get_title_or_name(),
                          'mtime': page.get_mtime(),
                          'last_author': user_title})

        sortby = context.get_form_values('sortby', sortby)
        sortorder = context.get_form_value('sortorder', sortorder)
        pages.sort(key=itemgetter(sortby[0]), reverse=(sortorder == 'down'))
        namespace['pages'] = pages

        columns = [
            ('name', u'Name'), ('title', u'Title'), ('mtime', u'Last Modified'),
            ('last_author', u'Last Author')]
        namespace['table'] = table(columns, pages, sortby, sortorder, [],
                self.gettext)

        handler = self.get_handler('/ui/Folder_browse_list.xml')
        return stl(handler, namespace)


register_object_class(WikiFolder)



class WikiPage(Text):
    class_id = 'WikiPage'
    class_version = '20061229'
    class_title = u"Wiki Page"
    class_description = u"Wiki contents"
    class_icon16 = 'images/WikiPage16.png'
    class_icon48 = 'images/WikiPage48.png'
    class_views = Text.class_views + [
            ['browse_content'],
            ['last_changes'],
            ['to_pdf']]
    class_extension = None

    overrides = {
        # Security
        'file_insertion_enabled': 0,
        'raw_enabled': 0,
        # Encodings
        'input_encoding': 'utf-8',
        'output_encoding': 'utf-8',
    }

    _wikiTagRE = re.compile(r'(<a [^>]* href=")!(.*?)("[^>]*>)(.*?)(</a>)',
                            re.I+re.S)
    link_template = ('%(open_tag)s../%(page)s%(open_tag_end)'
            's%(text)s%(end_tag)s')
    new_link_template = ('<span class="nowiki">%(text)s%(open_tag)s'
            '../;new_resource_form?type=WikiPage&name=%(page)s'
            '%(open_tag_end)s?%(end_tag)s</span>')



    def _resolve_wiki_link(self, match):
        namespace = {'open_tag': match.group(1),
                     'page': checkid(match.group(2)) or '',
                     'open_tag_end': match.group(3),
                     'text': match.group(4),
                     'end_tag': match.group(5)}
        parent = self.parent
        name = checkid(namespace['page']) or ''
        if parent.has_handler(name):
            return self.link_template % namespace
        else:
            return  self.new_link_template % namespace


    def _resolve_wiki_links(self, html):
        return self._wikiTagRE.sub(self._resolve_wiki_link, html)


    #######################################################################
    # User interface
    #######################################################################
    @classmethod
    def new_instance_form(cls, name=''):
        context = get_context()
        root = context.root
        namespace = {}

        # Page name
        name = context.get_form_value('name', default=u'', type=Unicode)
        namespace['name'] = checkid(name) or False

        # Class id
        namespace['class_id'] = cls.class_id

        handler = root.get_handler('ui/WikiPage_new_instance.xml')
        return stl(handler, namespace)


    def GET(self, context):
        return context.uri.resolve2(';view')


    def to_html(self):
        parent = self.parent

        # Override dandling links handling
        StandaloneReader = readers.get_reader_class('standalone')
        class WikiReader(StandaloneReader):
            supported = ('wiki',)

            def wiki_reference_resolver(target):
                refname = target['name']
                name = checkid(refname)
                target['wiki_name'] = name
                if parent.has_handler(name):
                    target['wiki_refname'] = refname
                else:
                    target['wiki_refname'] = False
                return True

            wiki_reference_resolver.priority = 851
            unknown_reference_resolvers = [wiki_reference_resolver]

        # Manipulate publisher directly (from publish_doctree)
        reader = WikiReader(parser_name='restructuredtext')
        pub = core.Publisher(reader=reader, source_class=io.StringInput,
                destination_class=io.NullOutput)
        pub.set_components(None, 'restructuredtext', 'null')
        pub.process_programmatic_settings(None, self.overrides, None)
        pub.set_source(self.to_str(), None)
        pub.set_destination(None, None)

        # Publish!
        pub.publish(enable_exit_status=None)
        document = pub.document

        # Fix the wiki links
        for node in document.traverse(condition=nodes.reference):
            refname = node.get('wiki_refname')
            if refname is None:
                if node.get('refid'):
                    node['classes'].append('internal')
                elif node.get('refuri'):
                    node['classes'].append('external')
            else:
                name = node['wiki_name']
                if refname is False:
                    refuri = ";new_resource_form?type=%s&name=%s"
                    refuri = refuri % (self.__class__.__name__, name)
                    css_class = 'nowiki'
                else:
                    refuri = name
                    css_class = 'wiki'
                node['refuri'] = '../' + refuri
                node['classes'].append(css_class)

        # Manipulate publisher directly (from publish_from_doctree)
        reader = readers.doctree.Reader(parser_name='null')
        pub = core.Publisher(reader, None, None,
                source=io.DocTreeInput(document),
                destination_class=io.StringOutput)
        pub.set_writer('html')
        pub.process_programmatic_settings(None, self.overrides, None)
        pub.set_destination(None, None)
        pub.publish(enable_exit_status=None)
        parts = pub.writer.parts
        body = parts['html_body']

        return body.encode('utf_8')


    to_pdf__access__ = 'is_allowed_to_view'
    to_pdf__label__ = u"To PDF"
    def to_pdf(self, context):
        parent = self.parent
        pages = [self.name]
        images = []

        # Override dandling links handling
        StandaloneReader = readers.get_reader_class('standalone')
        class WikiReader(StandaloneReader):
            supported = ('wiki',)

            def wiki_reference_resolver(target):
                refname = target['name']
                name = checkid(refname)
                if parent.has_handler(name):
                    if refname not in pages:
                        pages.append(refname)
                    target['wiki_refname'] = refname
                    target['wiki_name'] = name
                    return True
                else:
                    return False

            wiki_reference_resolver.priority = 851
            unknown_reference_resolvers = [wiki_reference_resolver]

        # Manipulate publisher directly (from publish_doctree)
        reader = WikiReader(parser_name='restructuredtext')
        pub = core.Publisher(reader=reader, source_class=io.StringInput,
                destination_class=io.NullOutput)
        pub.set_components(None, 'restructuredtext', 'null')
        pub.process_programmatic_settings(None, self.overrides, None)
        pub.set_source(self.to_str(), None)
        pub.set_destination(None, None)
        pub.publish(enable_exit_status=None)
        document = pub.document

        # Fix the wiki links
        for node in document.traverse(condition=nodes.reference):
            refname = node.get('wiki_refname')
            if refname is None:
                continue
            name = node['name'].lower()
            document.nameids[name] = refname
            
        # Append referenced pages
        for refname in pages[1:]:
            references = document.refnames[refname.lower()]
            reference = references[0]
            name = reference['wiki_name']
            title = reference.astext()
            page = parent.get_handler(name)
            source = page.to_str()
            subdoc = core.publish_doctree(source,
                    settings_overrides=self.overrides)
            # Remove ".. contents"
            for node in subdoc.traverse(condition=nodes.topic):
                if 'contents' in node['names']:
                    node.parent.remove(node)
            children = subdoc.children
            if not isinstance(children[0], nodes.title):
                children.insert(0, nodes.title(rawsource=title, text=title))
            attributes = {'ids': [refname], 'names': [title]}
            section = nodes.section(source, *children, **attributes)
            document.append(section)

        # Find the list of images to append
        for node in document.traverse(condition=nodes.image):
            node_uri = node['uri']
            if self.has_handler(node_uri):
                reference = uri.get_reference(node_uri)
                path = reference.path
                filename = str(path[-1])
                name, ext, lang = FileName.decode(filename)
                if ext == 'jpeg':
                    # pdflatex does not support this extension
                    ext = 'jpg'
                filename = FileName.encode((name, ext, lang))
                # Remove all path so the image is found in tempdir
                node['uri'] = filename
                images.append((node_uri, filename))

        overrides = dict(self.overrides)
        overrides['stylesheet'] = 'style.tex'
        output = core.publish_from_doctree(document, writer_name='latex',
                settings_overrides=overrides)

        dirname = mkdtemp('wiki', 'itools')
        tempdir = vfs.open(dirname)

        # Save the document...
        with tempdir.make_file(self.name) as file:
            file.write(output)
        # The stylesheet...
        stylesheet = self.get_handler('/ui/wiki/style.tex')
        with tempdir.make_file('style.tex') as file:
            stylesheet.save_state_to_file(file)
        # The 'powered' image...
        image = self.get_handler('/ui/images/ikaaro_powered.png')
        with tempdir.make_file('ikaaro.png') as file:
            image.save_state_to_file(file)
        # And referenced images
        for node_uri, filename in images:
            image = self.get_handler(node_uri)
            with tempdir.make_file(filename) as file:
                image.save_state_to_file(file)

        call(['pdflatex', self.name], cwd=dirname)
        # Twice for correct page numbering
        call(['pdflatex', self.name], cwd=dirname)

        pdfname = '%s.pdf' % self.name
        try:
            with tempdir.open(pdfname) as file:
                data = file.read()
        except LookupError:
            data = None
        vfs.remove(dirname)

        if data is None:
            message = u"PDF generation failed."
            return context.come_back(message)

        response = context.response
        response.set_header('Content-Type', 'application/pdf')
        response.set_header('Content-Disposition',
                'attachment; filename=%s' % pdfname)

        return data


    def view(self, context):
        css = self.get_handler('/ui/wiki.css')
        context.styles.append(str(self.get_pathto(css)))

        return self.to_html()


    def edit_form(self, context):
        css = self.get_handler('/ui/wiki.css')
        context.styles.append(str(self.get_pathto(css)))

        namespace = {}
        namespace['data'] = self.to_str()

        handler = self.get_handler('/ui/WikiPage_edit.xml')
        return stl(handler, namespace)


    def edit(self, context):
        goto = Text.edit(self, context)

        message = goto.query['message']
        if 'class="system-message"' in self.to_html():
            message = u"Syntax error, please check the view for details."

        if context.has_form_value('view'):
            goto = ';view'
        else:
            goto.fragment = 'bottom'
        return context.come_back(message, goto)


    browse_content__access__ = WikiFolder.browse_content__access__
    browse_content__label__ = WikiFolder.browse_content__label__
    def browse_content(self, context):
        return context.uri.resolve('../;browse_content')


    last_changes__access__ = WikiFolder.last_changes__access__
    last_changes__label__ = WikiFolder.last_changes__label__
    def last_changes(self, context):
        return context.uri.resolve('../;last_changes')


register_object_class(WikiPage)
