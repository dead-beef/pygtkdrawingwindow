#!/usr/bin/env python

from __future__ import print_function

try:
    import pygtk
    pygtk.require('2.0')
    import gobject
    import gtk
except ImportError:
    from gi.repository import Gtk as gtk, GObject as gobject

import sys

from pygtkdrawingwindow import ImageWindow


def main():
    if len(sys.argv) != 2:
        print('Usage:', sys.argv[0], '<image>')
        exit(1)

    try:
        toolbar_style = gtk.TOOLBAR_ICONS
    except AttributeError:
        toolbar_style = gtk.ToolbarStyle.ICONS

    gobject.threads_init()

    wnd = gtk.Window()
    wnd.set_default_size(400, 300)

    img = ImageWindow(sys.argv[1])
    #img = ImageWindow(gtk.image_new_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_MENU))

    vbox = gtk.VBox()
    wnd.add(vbox)

    toolbar = gtk.Toolbar()
    toolbar.set_style(toolbar_style)

    btn = gtk.ToolButton(gtk.STOCK_ZOOM_IN)
    btn.set_tooltip_text('Zoom In')
    btn.connect('clicked', img.zoom_in)
    toolbar.insert(btn, -1)

    btn = gtk.ToolButton(gtk.STOCK_ZOOM_OUT)
    btn.set_tooltip_text('Zoom Out')
    btn.connect('clicked', img.zoom_out)
    toolbar.insert(btn, -1)

    btn = gtk.ToolButton(gtk.STOCK_ZOOM_FIT)
    btn.set_tooltip_text('Fit')
    btn.connect('clicked', img.zoom_fit)
    toolbar.insert(btn, -1)

    btn = gtk.ToolButton(gtk.STOCK_ZOOM_FIT)
    btn.set_tooltip_text('Fit Width')
    btn.connect('clicked', img.zoom_fit_width)
    toolbar.insert(btn, -1)

    btn = gtk.ToolButton(gtk.STOCK_ZOOM_FIT)
    btn.set_tooltip_text('Fit Height')
    btn.connect('clicked', img.zoom_fit_height)
    toolbar.insert(btn, -1)

    btn = gtk.ToolButton(gtk.STOCK_ZOOM_FIT)
    btn.set_tooltip_text('Fit or 1:1')
    btn.connect('clicked', img.zoom_fit_or_1to1)
    toolbar.insert(btn, -1)

    vbox.pack_start(toolbar, False, False, 0)
    vbox.pack_start(img, True, True, 0)

    wnd.connect('destroy', gtk.main_quit)
    wnd.show_all()

    gtk.main()

main()
