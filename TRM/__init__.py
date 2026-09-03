"""SpotAxis project package.

The only runtime setup here is a macOS-specific library path shim so that
WeasyPrint (loaded through cffi) can find Homebrew's Pango/GLib/cairo when
Django is started from a shell whose ``DYLD_*`` variables were stripped by
System Integrity Protection. It is a no-op everywhere else.
"""
import os
import sys

if sys.platform == 'darwin':
    _brew_lib_dirs = [d for d in ('/opt/homebrew/lib', '/usr/local/lib') if os.path.isdir(d)]
    if _brew_lib_dirs:
        _current = os.environ.get('DYLD_FALLBACK_LIBRARY_PATH', '')
        _missing = [d for d in _brew_lib_dirs if d not in _current.split(':')]
        if _missing:
            os.environ['DYLD_FALLBACK_LIBRARY_PATH'] = ':'.join(_missing + ([_current] if _current else []))
