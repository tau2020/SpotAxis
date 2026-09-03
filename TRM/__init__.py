# These lines are provisional as a new version
# of MySQLdb: http://sourceforge.net/projects/mysql-python
# that supports Python3.X
# TODO: Quitar estas lineas cuando MySQLdb soporte Python.X
from __future__ import absolute_import
import os
import sys

import pymysql
pymysql.install_as_MySQLdb()

# WeasyPrint loads Pango/GLib/cairo through cffi's dlopen, which on macOS only
# searches the system paths plus DYLD_FALLBACK_LIBRARY_PATH. Homebrew installs
# those libraries under a prefix that is not on that list, and System Integrity
# Protection strips DYLD_* variables from the environment whenever a protected
# binary (/bin/sh, /usr/bin/env, ...) spawns the interpreter -- so exporting the
# variable in a shell is not reliable. Setting it here instead is enough:
# ctypes.util.find_library() reads it from os.environ at call time.
if sys.platform == 'darwin':
    _lib_dirs = [
        path for path in ('/opt/homebrew/lib', '/usr/local/lib')
        if os.path.isdir(path)
    ]
    _existing = os.environ.get('DYLD_FALLBACK_LIBRARY_PATH', '')
    _search_path = os.pathsep.join(
        [p for p in _existing.split(os.pathsep) if p] + _lib_dirs
    )
    if _search_path:
        os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = _search_path

# Compatibility shim: django-tagging 0.5.0 (pulled in for the optional `zinnia`
# blog app) still imports django.utils.encoding.smart_text, which Django removed
# in 4.0 in favour of smart_str. Aliasing it here keeps the app registry loadable
# without vendoring or forking django-tagging.
from django.utils import encoding as _django_encoding

if not hasattr(_django_encoding, 'smart_text'):
    _django_encoding.smart_text = _django_encoding.smart_str
