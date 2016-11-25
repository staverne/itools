# -*- coding: UTF-8 -*-
# Copyright (C) 2016 Sylvain Taverne <sylvain@agicia.com>
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

# Import from standard library
from cStringIO import StringIO

# Import from PIL
from PIL import Image as PILImage

# Import from itools
from itools.gettext import MSG

# Import from here
from base import BaseValidator
from exceptions import ValidationError



class FileExtensionValidator(BaseValidator):

    validator_id = 'file-extension'
    allowed_extensions = []
    errors = {'invalid_extension': MSG(
            u"File extension '{extension}' is not allowed. "
            u"Allowed extensions are: '{allowed_extensions}'.")}


    def check(self, value):
        extension = self.get_extension(value)
        if extension not in self.allowed_extensions:
            kw = {'value': value}
            self.raise_default_error(kw)


    def get_extension(self, value):
        filename, mimetype, body = value
        return filename.split('.')[-1]



class ImageExtensionValidator(FileExtensionValidator):

    validator_id = 'image-extension'
    allowed_extensions = ['jpeg', 'png', 'gif']



class MimetypesValidator(BaseValidator):

    validator_id = 'mimetypes'
    authorized_mimetypes = []
    errors = {'bad_mimetype': MSG(u"XXX")}


    def check(self, value):
        filename, mimetype, body = value
        if mimetype not in self.authorized_mimetypes:
            kw = {'value': value}
            self.raise_default_error(kw)



class ImageMimetypesValidator(MimetypesValidator):

    validator_id = 'image-mimetypes'
    authorized_mimetypes = ['image/jpeg', 'image/png', 'image/gif']



class FileSizeValidator(BaseValidator):

    validator_id = 'file-size'
    max_size = 1024*1024*10
    errors = {'too_big': MSG(u'XXX')}

    def check(self, value):
        filename, mimetype, body = value
        size = len(body)
        if size > self.max_size:
            kw = {'size': size}
            self.raise_default_error(kw)



class ImagePixelsValidator(BaseValidator):

    validator_id = 'image-pixels'
    max_pixels = 2000*2000

    errors = {'too_much_pixels': MSG(u"L'image est trop grande."),
              'image_has_errors': MSG(u"L'image contient des erreurs")}

    def check(self, value):
        filename, mimetype, body = value
        data = StringIO(body)
        try:
            im = PILImage.open(data)
            im.verify()
        except Exception:
            code = 'image_has_errors'
            raise ValidationError(code, self.errors[code], {})
        if im.width * im.height > self.max_pixels:
            code = 'too_much_pixels'
            raise ValidationError(code, self.errors[code], {})
