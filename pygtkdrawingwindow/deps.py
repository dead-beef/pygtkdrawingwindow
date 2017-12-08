# pylint:disable=import-error,no-name-in-module,unused-import

from __future__ import division, print_function, absolute_import, with_statement

import sys
from enum import IntEnum

import cairo

try:
    if 'gi' in sys.modules:
        raise ImportError('use gi')

    import pygtk
    pygtk.require('2.0')
    import glib
    import gobject
    import gtk
    from gtk import gdk
    from gtk.gdk import Pixbuf, PixbufAnimation

    TimeVal = None

    try:
        import rsvg
    except ImportError:
        rsvg = None

    PYGTK = True
except ImportError:
    from gi.repository import (
        Gtk as gtk,
        Gdk as gdk,
        GLib as glib,
        GObject as gobject
    )
    from gi.repository.Gtk import ImageType, PolicyType, IconSize
    from gi.repository.Gdk import ScrollDirection
    from gi.repository.GdkPixbuf import Pixbuf, PixbufAnimation

    try:
        from gi.repository.GLib import TimeVal
    except ImportError:
        TimeVal = None

    try:
        from gi.repository import Rsvg as rsvg
    except ImportError:
        rsvg = None

    PYGTK = False


class NoRsvg(object):
    """Missing rsvg module class.

    Examples
    --------
    >>> rsvg = NoRsvg
    >>> rsvg.Handle('image.svg')
    glib.GError: missing rsvg module
    >>> rsvg.Handle.new_from_file('image.svg')
    glib.GError: missing rsvg module
    """
    class Handle(object):
        """rsvg handle class.
        """
        @staticmethod
        def error():
            """Throw missing module error.

            Raises
            ------
            glib.GError
            """
            raise glib.GError('missing rsvg module')

        def __init__(self, *_):
            """Throw missing module error.

            Parameters
            ----------
            *_
                Unused.

            Raises
            ------
            glib.GError
            """
            self.error()

        @classmethod
        def new_from_file(cls, *_):
            """Throw missing module error.

            Parameters
            ----------
            *_
                Unused.

            Raises
            ------
            glib.GError
            """
            cls.error()


if rsvg is None:
    rsvg = NoRsvg

try:
    from itertools import izip
except ImportError:
    izip = zip

try:
    STRING_TYPES = (str, unicode)
except NameError:
    STRING_TYPES = (str, bytes)

if PYGTK:
    gtk_image_new_from_file = gtk.image_new_from_file
    gtk_image_new_from_stock = gtk.image_new_from_stock
    cairo_set_source_pixbuf = gdk.CairoContext.set_source_pixbuf
    rsvg_handle_new_from_file = rsvg.Handle

    class ImageType(IntEnum): # pylint:disable=function-redefined
        """PyGTK image types.
        """
        EMPTY = gtk.IMAGE_EMPTY
        PIXBUF = gtk.IMAGE_PIXBUF
        ANIMATION = gtk.IMAGE_ANIMATION
        IMAGE = gtk.IMAGE_IMAGE
        PIXMAP = gtk.IMAGE_PIXMAP
        STOCK = gtk.IMAGE_STOCK
        ICON_SET = gtk.IMAGE_ICON_SET

    class PolicyType(IntEnum): # pylint:disable=function-redefined
        """PyGTK scrollbar policy types.
        """
        ALWAYS = gtk.POLICY_ALWAYS
        AUTOMATIC = gtk.POLICY_AUTOMATIC
        NEVER = gtk.POLICY_NEVER

    class ScrollDirection(IntEnum): # pylint:disable=function-redefined
        """PyGTK scroll directions.
        """
        UP = gdk.SCROLL_UP
        DOWN = gdk.SCROLL_DOWN
        LEFT = gdk.SCROLL_LEFT
        RIGHT = gdk.SCROLL_RIGHT
        SMOOTH = -1

    class IconSize(IntEnum): # pylint:disable=function-redefined
        """PyGTK icon sizes.
        """
        DIALOG = gtk.ICON_SIZE_DIALOG

else:
    gtk_image_new_from_file = gtk.Image.new_from_file
    gtk_image_new_from_stock = gtk.Image.new_from_stock
    cairo_set_source_pixbuf = gdk.cairo_set_source_pixbuf
    rsvg_handle_new_from_file = rsvg.Handle.new_from_file
