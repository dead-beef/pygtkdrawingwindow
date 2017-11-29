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

import sys
from math import ceil, floor

from pygtkdrawingwindow import ImageWindow, ignore_args


if PYGTK:
    TOOLBAR_STYLE = gtk.TOOLBAR_BOTH
    WINDOW_POSITION = gtk.WIN_POS_CENTER
else:
    TOOLBAR_STYLE = gtk.ToolbarStyle.BOTH
    WINDOW_POSITION = gtk.WindowPosition.CENTER

try:
    xrange
except NameError:
    xrange = range # pylint:disable=redefined-builtin


def toolbutton(icon, label, onclick, sensitive=True):
    btn = gtk.ToolButton(icon_widget=None, label=label)
    btn.set_stock_id(icon)
    if isinstance(onclick, tuple):
        btn.connect('clicked', *onclick)
    else:
        btn.connect('clicked', ignore_args(onclick))
    btn.set_sensitive(sensitive)
    return btn

def draw_grid(widget, ctx):
    zoom = widget.get_zoom()
    #if zoom < 16.0:
    #    return

    width, height = widget.get_size()
    left, up, right, down = ctx.clip_extents()
    left = max(0, int(floor(left)))
    right = min(width, int(ceil(right))) + 1
    up = max(0, int(floor(up)))
    down = min(height, int(ceil(down))) + 1

    ctx.set_source_rgb(0.0, 0.0, 0.0)
    ctx.set_line_width(0.5 / zoom)
    for x in xrange(left, right):
        ctx.move_to(x, up)
        ctx.line_to(x, down)
    for y in xrange(up, down):
        ctx.move_to(left, y)
        ctx.line_to(right, y)
    ctx.stroke()

def toggle_grid(_, img, grid):
    if grid[0] is None:
        grid[0] = img.connect('render', draw_grid)
    else:
        img.disconnect(grid[0])
        grid[0] = None
    img.queue_draw()

def toggle_animation(btn, img):
    state = not img.get_animation()
    img.set_animation(state)
    btn.set_stock_id(gtk.STOCK_MEDIA_PAUSE if state else gtk.STOCK_MEDIA_PLAY)
    btn.queue_draw()

def main():
    if len(sys.argv) != 2:
        print('Usage:', sys.argv[0], '<image>')
        exit(1)

    grid = [None]

    wnd = gtk.Window()
    wnd.set_title('ImageWindow')
    wnd.set_default_size(1024, 600)
    wnd.set_position(WINDOW_POSITION)

    img = ImageWindow()
    img.set_image(sys.argv[1])
    #toggle_grid(None, img, grid)

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
        (gtk.STOCK_ZOOM_FIT, 'Fit or 1:1', img.zoom_fit_or_1to1),
        (gtk.STOCK_SELECT_COLOR, 'Toggle Grid', (toggle_grid, img, grid)),
        (gtk.STOCK_MEDIA_PAUSE if img.has_animation() else gtk.STOCK_MEDIA_PLAY,
         'Toggle Animation', (toggle_animation, img), img.has_animation())
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
