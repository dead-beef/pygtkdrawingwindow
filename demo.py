#!/usr/bin/env python2

import pygtk
pygtk.require('2.0')
import gobject
import gtk

import sys

from pygtkdrawingwindow import ImageWindow


def main():
    if len(sys.argv) != 2:
        print 'Usage:', sys.argv[0], '<image>'
        exit(1)

    gobject.threads_init()

    wnd = gtk.Window()
    wnd.set_default_size(400, 300)

    img = ImageWindow(sys.argv[1])

    vbox = gtk.VBox()
    wnd.add(vbox)

    toolbar = gtk.Toolbar()
    toolbar.set_style(gtk.TOOLBAR_ICONS)

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

    vbox.pack_start(toolbar, False, False)
    vbox.pack_start(img)

    wnd.connect('destroy', gtk.main_quit)
    wnd.show_all()

    gtk.main()

main()
