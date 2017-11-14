#!/usr/bin/env python

from __future__ import print_function

try:
    import pygtk
    pygtk.require('2.0')
    import gtk

    PYGTK = True
except ImportError:
    from gi.repository import Gtk as gtk

    PYGTK = False

import sys
from math import ceil, floor

from pygtkdrawingwindow import ImageWindow


if PYGTK:
    gtk_image_new_from_stock = gtk.image_new_from_stock
    ICON_SIZE = gtk.ICON_SIZE_MENU
    TOOLBAR_STYLE = gtk.TOOLBAR_BOTH
else:
    gtk_image_new_from_stock = gtk.Image.new_from_stock
    ICON_SIZE = gtk.IconSize.MENU
    TOOLBAR_STYLE = gtk.ToolbarStyle.BOTH

try:
    xrange
except NameError:
    xrange = range


class ImageDemo(ImageWindow):
    def __init__(self, *args, **kwargs):
        super(ImageDemo, self).__init__(*args, **kwargs)
        self.grid = True

    def toggle_grid(self, *_):
        self.grid = not self.grid
        self.queue_draw()

    def render(self, ctx):
        super(ImageDemo, self).render(ctx)

        if self.grid:
            width, height = self.size
            left, up, right, down = ctx.clip_extents()
            left = max(0, int(floor(left)))
            right = min(width, int(ceil(right))) + 1
            up = max(0, int(floor(up)))
            down = min(height, int(ceil(down))) + 1

            ctx.set_source_rgb(0.0, 0.0, 0.0)
            ctx.set_line_width(0.5 / self.scale)
            for x in xrange(left, right):
                ctx.move_to(x, up)
                ctx.line_to(x, down)
                ctx.stroke()
            for y in xrange(up, down):
                ctx.move_to(left, y)
                ctx.line_to(right, y)
                ctx.stroke()


def toolbutton(icon, label, onclick):
    btn = gtk.ToolButton(
        icon_widget=gtk_image_new_from_stock(icon, ICON_SIZE),
        label=label
    )
    btn.connect('clicked', onclick)
    return btn

def main():
    if len(sys.argv) != 2:
        print('Usage:', sys.argv[0], '<image>')
        exit(1)

    wnd = gtk.Window()
    wnd.set_title('pygtkdrawingwindow demo')
    wnd.set_default_size(800, 600)

    img = ImageDemo(sys.argv[1])

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
        (gtk.STOCK_SELECT_COLOR, 'Toggle Grid', img.toggle_grid)
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
