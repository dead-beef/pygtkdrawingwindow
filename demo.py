#!/usr/bin/env python

from __future__ import print_function

try:
    import pygtk
    pygtk.require('2.0')
    import gtk
    PYGTK = True
except ImportError:
    from gi.repository import Gtk as gtk # pylint:disable=no-name-in-module
    PYGTK = False

from pygtkdrawingwindow import DrawingWindow
from pygtkdrawingwindow.util import ignore_args


if PYGTK:
    TOOLBAR_STYLE = gtk.TOOLBAR_BOTH
    WINDOW_POSITION = gtk.WIN_POS_CENTER
else:
    TOOLBAR_STYLE = gtk.ToolbarStyle.BOTH
    WINDOW_POSITION = gtk.WindowPosition.CENTER


def toolbutton(icon, label, onclick):
    btn = gtk.ToolButton(icon_widget=None, label=label)
    btn.set_stock_id(icon)
    btn.connect('clicked', ignore_args(onclick))
    return btn

def draw(widget, ctx):
    width, height = widget.get_size()
    ctx.set_source_rgb(1.0, 0.5, 1.0)
    ctx.set_line_width(4)
    ctx.rectangle(0, 0, width, height)
    ctx.move_to(0, 0)
    ctx.line_to(width, height)
    ctx.move_to(width, 0)
    ctx.line_to(0, height)
    ctx.stroke()

def main():
    wnd = gtk.Window()
    wnd.set_title('DrawingWindow')
    wnd.set_default_size(800, 600)
    wnd.set_position(WINDOW_POSITION)

    img = DrawingWindow()
    img.set_size(200, 200)
    img.connect('render', draw)

    vbox = gtk.VBox()
    wnd.add(vbox)

    toolbar = gtk.Toolbar()
    toolbar.set_style(TOOLBAR_STYLE)

    toolbuttons = [
        (gtk.STOCK_ZOOM_IN, 'Zoom In', img.zoom_in),
        (gtk.STOCK_ZOOM_OUT, 'Zoom Out', img.zoom_out),
        (gtk.STOCK_ZOOM_FIT, 'Fit', img.zoom_fit),
        (gtk.STOCK_ZOOM_FIT, 'Fit Width', img.zoom_fit_width),
        (gtk.STOCK_ZOOM_FIT, 'Fit Height', img.zoom_fit_height),
        (gtk.STOCK_ZOOM_FIT, 'Fit or 1:1', img.zoom_fit_or_1to1)
    ]

    for btn in toolbuttons:
        toolbar.insert(toolbutton(*btn), -1)

    vbox.pack_start(toolbar, False, False, 0)
    vbox.pack_start(img, True, True, 0)

    wnd.connect('destroy', gtk.main_quit)
    wnd.show_all()

    gtk.main()


if __name__ == '__main__':
    main()
