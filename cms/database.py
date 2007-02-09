# -*- coding: UTF-8 -*-
# Copyright (C) 2006 Juan David Ibáñez Palomar <jdavid@itaapy.com>
# Copyright (C) 2006 Hervé Cauwelier <herve@itaapy.com>
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

# Import from the Standard Library
import thread
from os import remove, rename
from subprocess import call

# Import from itools
from itools.vfs.file import FileFS
from itools.vfs.registry import register_file_system


def get_reference_on_change(reference):
    backup = '~' + reference.path[-1].name + '.tmp'
    return reference.resolve(backup)


def get_reference_on_add(reference):
    backup = '~' + reference.path[-1].name + '.add'
    return reference.resolve(backup)


def get_reference_on_remove(reference):
    backup = '~' + reference.path[-1].name + '.del'
    return reference.resolve(backup)



thread_lock = thread.allocate_lock()
_transactions = {}


def get_transaction():
    ident = thread.get_ident()
    thread_lock.acquire()
    try:
        transaction = _transactions.setdefault(ident, set())
    finally:
        thread_lock.release()

    return transaction



class DatabaseFS(FileFS):

    @staticmethod
    def make_file(reference):
        # The catalog has its own backup
        if '.catalog' in reference.path:
            return FileFS.make_file(reference)

        marker = get_reference_on_add(reference)
        FileFS.make_file(marker)
        get_transaction().add(marker)
        return FileFS.make_file(reference)


    @staticmethod
    def make_folder(reference):
        # The catalog has its own backup
        if '.catalog' in reference.path:
            return FileFS.make_folder(reference)

        marker = get_reference_on_add(reference)
        FileFS.make_file(marker)
        get_transaction().add(marker)
        return FileFS.make_folder(reference)


    @staticmethod
    def remove(reference):
        # The catalog has its own backup
        if '.catalog' in reference.path:
            return FileFS.remove(reference)

        src = str(reference.path)
        reference = get_reference_on_remove(reference)
        get_transaction().add(reference)
        dst = str(reference.path)
        rename(src, dst)


    @staticmethod
    def open(reference, mode=None):
        # The catalog has its own backup
        if '.catalog' in reference.path:
            return FileFS.open(reference, mode)

        if mode == 'w':
            reference = get_reference_on_change(reference)
            if FileFS.exists(reference):
                return FileFS.open(reference, mode)
            get_transaction().add(reference)
            return FileFS.make_file(reference)

        return FileFS.open(reference, mode)


    @staticmethod
    def commit_transaction(database):
        transaction = get_transaction()
        for reference in transaction:
            path = reference.path
            filename = path[-1].name
            marker = filename[-3:]
            original = str(path.resolve(filename[1:-4]))
            if marker == 'tmp':
                remove(original)
                backup = str(path)
                rename(backup, original)
            elif marker == 'add' or marker == 'del':
                FileFS.remove(reference)
        transaction.clear()
        src = str(database.path.resolve2('.catalog/'))
        dst = str(database.path.resolve2('.catalog.bak'))
        call(['rsync', '-a', '--delete', src, dst])


    @staticmethod
    def rollback_transaction(database):
        transaction = get_transaction()
        for reference in transaction:
            path = reference.path
            filename = path[-1].name
            marker = filename[-3:]
            original = path.resolve(filename[1:-4])
            backup = str(path)
            if marker == 'tmp':
                remove(backup)
            elif marker == 'add':
                FileFS.remove(original)
                remove(backup)
            elif marker == 'del':
                original = str(original)
                rename(backup, original)
        transaction.clear()
        src = str(database.path.resolve2('.catalog.bak/'))
        dst = str(database.path.resolve2('.catalog'))
        call(['rsync', '-a', '--delete', src, dst])


    @staticmethod
    def commit_all(database):
        stack = [database]
        while stack:
            folder = stack.pop()
            for name in folder.get_names():
                if name[0] == '~':
                    marker = name[-3:]
                    original = name[1:-4]
                    if marker == 'tmp':
                        if folder.exists(original):
                            folder.remove(original)
                        folder.move(name, original)
                    elif marker == 'add' or marker == 'del':
                        folder.remove(name)
                elif name == '.catalog':
                    src = str(folder.uri.path.resolve2('.catalog/'))
                    dst = str(folder.uri.path.resolve2('.catalog.bak'))
                    call(['rsync', '-a', '--delete', src, dst])
                elif name == '.catalog.bak':
                    continue
                elif folder.is_folder(name):
                    stack.append(folder.open(name))


    @staticmethod
    def rollback_all(database):
        stack = [database]
        while stack:
            folder = stack.pop()
            # Process the markers first
            for name in folder.get_names():
                if name[0] == '~':
                    marker = name[-3:]
                    original = name[1:-4]
                    if marker == 'tmp':
                        folder.remove(name)
                    elif marker == 'add':
                        folder.remove(original)
                        folder.remove(name)
                    elif marker == 'del':
                        if folder.exists(original):
                            folder.remove(original)
                        folder.move(name, original)
            # Process the others
            for name in folder.get_names():
                if name == '.catalog':
                    src = str(folder.uri.path.resolve2('.catalog.bak/'))
                    dst = str(folder.uri.path.resolve2('.catalog'))
                    call(['rsync', '-a', '--delete', src, dst])
                elif name == '.catalog.bak':
                    continue
                elif folder.is_folder(name):
                    stack.append(folder.open(name))



register_file_system('database', DatabaseFS)
