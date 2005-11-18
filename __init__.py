# -*- coding: ISO-8859-1 -*-
# Copyright (C) 2002-2005 Juan David Ib��ez Palomar <jdavid@itaapy.com>
#                    2005 Luis Belmar Letelier <luis@itaapy.com>
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


# Import from the Standard Library
import os
import sys


def get_abspath(globals_namespace, local_path):
    """
    Returns the absolute path to the required file.
    """
    mname = globals_namespace['__name__']

    if mname == '__main__':
        mpath = os.getcwd()
    else:
        module = sys.modules[mname]
        if hasattr(module, '__path__'):
            mpath = module.__path__[0]
        elif '.' in mname:
            mpath = sys.modules[mname[:mname.rfind('.')]].__path__[0]
        else:
            mpath = mname

    drive, mpath = os.path.splitdrive(mpath)
    mpath = drive + os.path.join(mpath, local_path)

    # Make it working with Windows. Internally we use always the "/".
    if os.path.sep == '\\':
        mpath = mpath.replace(os.path.sep, '/')

    return mpath



def get_arch_revision():
    """
    Get the arch revision name from the Changelog file.
    """
    changelog_path = get_abspath(globals(), 'Changelog')

    # Open Changelog file and take the first line after the first 'Revision:'
    try:
        file = open(changelog_path, 'r')
    except IOError:
        print 'arch revision of itools: not found '
        tla_revision = None
    else:
        line = ''
        while not line.startswith('Revision:'):
            line = file.readline().strip()
        tla_revision = file.readline().strip()

    return tla_revision


__arch_revision__ = get_arch_revision()
