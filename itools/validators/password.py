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
from string import ascii_letters, digits

# Import from itools
from itools.gettext import MSG

# Import from here
from base import BaseValidator


class StrongPasswordValidator(BaseValidator):
    """
     au minimum un caractère spécial ( *?./+#!,;:=)
     at least one special character ( *?./+#!,;:=)
     at least a number (1, 2, 3, ...)"
    """
    min_length = 8

    errors = {
        'too_short': MSG(u"This password is too short. It must contain at least {min_length} characters.")
      }
    help_msg = MSG(u"Your password must contain at least {min_length} characters.")

    def check(self, value):
        has_letter = has_digit = has_special = False
        for c in value:
            if c in ascii_letters:
                has_letter = True
            elif c in digits:
                has_digit = True
            else:
                has_special = True
        if not has_letter or not has_digit or not has_special:
            self.raise_default_error()
