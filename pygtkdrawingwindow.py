from __future__ import division, print_function

import sys

from argparse import Namespace
from contextlib import contextmanager

import cairo

class NoRsvg(object):
    class Handle(object):
        @staticmethod
        def error():
            raise glib.GError('no rsvg')
        def __init__(self, *_):
            self.error()
        @classmethod
        def new_from_file(cls, *_):
            cls.error()

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

    try:
        import rsvg
    except ImportError:
        rsvg = NoRsvg

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
        from gi.repository import Rsvg as rsvg
    except ImportError:
        rsvg = NoRsvg

    PYGTK = False


from math import ceil, sin, cos
from itertools import product
from time import sleep

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

    ImageType = Namespace(
        EMPTY=gtk.IMAGE_EMPTY,
        PIXBUF=gtk.IMAGE_PIXBUF,
        ANIMATION=gtk.IMAGE_ANIMATION,
        IMAGE=gtk.IMAGE_IMAGE,
        PIXMAP=gtk.IMAGE_PIXMAP,
        STOCK=gtk.IMAGE_STOCK,
        ICON_SET=gtk.IMAGE_ICON_SET
    )
    PolicyType = Namespace(
        ALWAYS=gtk.POLICY_ALWAYS,
        AUTOMATIC=gtk.POLICY_AUTOMATIC,
        NEVER=gtk.POLICY_NEVER
    )
    ScrollDirection = Namespace(
        UP=gdk.SCROLL_UP,
        DOWN=gdk.SCROLL_DOWN,
        LEFT=gdk.SCROLL_LEFT,
        RIGHT=gdk.SCROLL_RIGHT,
        SMOOTH=None
    )
    IconSize = Namespace(
        DIALOG=gtk.ICON_SIZE_DIALOG
    )
else:
    gtk_image_new_from_file = gtk.Image.new_from_file
    gtk_image_new_from_stock = gtk.Image.new_from_stock
    cairo_set_source_pixbuf = gdk.cairo_set_source_pixbuf
    rsvg_handle_new_from_file = rsvg.Handle.new_from_file


class DrawingWindow(gtk.ScrolledWindow):

    FIT_LAST = -1
    FIT_NONE = 0
    FIT = 1
    FIT_WIDTH = 2
    FIT_HEIGHT = 3
    FIT_OR_1TO1 = 4

    if PYGTK:
        POLICY = gtk.POLICY_AUTOMATIC
        SHADOW = gtk.SHADOW_NONE
        EVENTS = gdk.POINTER_MOTION_MASK \
                 | gdk.POINTER_MOTION_HINT_MASK \
                 | gdk.LEAVE_NOTIFY_MASK \
                 | gdk.BUTTON_PRESS_MASK \
                 | gdk.BUTTON_MOTION_MASK
        BUTTON_MASK = gdk.BUTTON2_MASK | gdk.BUTTON1_MASK
    else:
        POLICY = gtk.PolicyType.AUTOMATIC
        SHADOW = gtk.ShadowType.NONE
        EVENTS = gdk.EventMask.POINTER_MOTION_MASK \
                 | gdk.EventMask.POINTER_MOTION_HINT_MASK \
                 | gdk.EventMask.LEAVE_NOTIFY_MASK \
                 | gdk.EventMask.BUTTON_PRESS_MASK \
                 | gdk.EventMask.BUTTON_MOTION_MASK
        BUTTON_MASK = gdk.ModifierType.BUTTON2_MASK \
                      | gdk.ModifierType.BUTTON1_MASK

    def __init__(self, fit=FIT_OR_1TO1, draw=None):
        super(DrawingWindow, self).__init__()

        self.set_policy(self.POLICY, self.POLICY)
        self.set_shadow_type(self.SHADOW)

        self.screen = gtk.DrawingArea()
        self.add_with_viewport(self.screen)

        self._scrollbar_size = 20
        self._fit_offset = 5
        self._prev_scale = None
        self._size = (0, 0)
        self._scale = None
        self._rotate = 0.0

        self._fit = (
            nop,
            self.zoom_fit,
            self.zoom_fit_width,
            self.zoom_fit_height,
            self.zoom_fit_or_1to1
        )
        self.fit = fit

        self.draw_func = draw

        self.pointer = None
        self.pointer_root = None

        self.scale = 1.0

        self.screen.set_events(self.EVENTS)
        #self.screen.set_double_buffered(False)
        self.connect('size_allocate', self.update_fit)
        self.connect('scroll_event', self.scroll_event)
        self.screen.connect('size_allocate', self.size_allocate_event)
        self.screen.connect('motion_notify_event', self.motion_notify_event)
        self.screen.connect('leave_notify_event', self.leave_notify_event)
        if PYGTK:
            self.screen.connect('expose_event', self.expose_event)
        else:
            self.screen.connect('draw', self.draw_event)

    def queue_draw(self):
        super(DrawingWindow, self).queue_draw()
        self.screen.queue_draw()

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        self.screen.set_size_request(*(int(sz * scale) for sz in self.size))
        if self._prev_scale is None:
            self._prev_scale = self._scale
        self._scale = scale

    @property
    def rotate(self):
        return self._rotate

    @rotate.setter
    def rotate(self, rotate):
        width, height = self.size
        width /= 2
        height /= 2
        rect = list(product((-width, width), (-height, height)))
        sin_, cos_ = sin(rotate), cos(rotate)
        for i, point in enumerate(rect):
            x, y = point
            rect[i] = (
                x * cos_ + y * sin_,
                y * cos_ - x * sin_
            )
        width = max(x for x, _ in rect) - min(x for x, _ in rect)
        height = max(y for _, y in rect) - min(y for _, y in rect)
        self.screen.set_size_request(
            int(ceil(width * self.scale)),
            int(ceil(height * self.scale))
        )
        self.screen.queue_draw()
        self._rotate = rotate

    @property
    def size(self):
        return self._size

    @size.setter
    def size(self, size):
        self._size = size
        self.scale = self.scale

    @property
    def window_size(self):
        rect = self.get_allocation()
        return rect.width, rect.height

    def _zoom_scroll(self):
        if self._prev_scale is None:
            return

        dscale = self.scale / self._prev_scale

        scrollbars = (self.get_hscrollbar(), self.get_vscrollbar())
        scrollbar_sizes = (
            scrollbars[1].get_allocation().width,
            scrollbars[0].get_allocation().height
        )
        maxsize = max(scrollbar_sizes)
        if maxsize > 1:
            self._scrollbar_size = maxsize

        if self.pointer is None:
            pointer = tuple(
                sb.get_value() + (wnd_size - sb_size) / 2
                for sb, sb_size, wnd_size
                in izip(scrollbars, scrollbar_sizes, self.window_size)
            )
        else:
            pointer = self.pointer
            self.pointer = tuple(x * dscale for x in pointer)

        dscale -= 1

        for x, scrollbar in izip(pointer, scrollbars):
            #adj = scrollbar.get_adjustment()
            value = scrollbar.get_value() + dscale * x
            #value = min(adj.get_upper(), max(adj.get_lower(), value))
            scrollbar.set_value(value)

        self._prev_scale = None

    def update_fit(self, *_):
        try:
            self._fit[self.fit]()
        except IndexError:
            self.fit = self.FIT_NONE
            raise

    def size_allocate_event(self, *_):
        with freeze(self.screen):
            self._zoom_scroll()
            self.update_fit()

    def expose_event(self, _, event):
        ctx = self.screen.get_window().cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        self.draw_event(None, ctx)

    def draw_event(self, _, ctx):
        width, height = self.size
        width *= 0.5
        height *= 0.5
        size = self.screen.get_allocation()
        size = (size.width, size.height)
        off = [max(0, (wnd_size - img_size * self.scale) / 2)
               for wnd_size, img_size in izip(size, self.size)]

        #ctx.identity_matrix()
        #ctx.save()
        ctx.translate(*off)
        ctx.scale(self.scale, self.scale)
        ctx.translate(width, height)
        ctx.rotate(self.rotate)
        ctx.translate(-width, -height)

        self.render(ctx)
        #ctx.restore()

    def leave_notify_event(self, *_):
        self.pointer = None
        self.pointer_root = None
        return False

    def motion_notify_event(self, _, event):
        ret = False

        self.pointer = (event.x, event.y)
        pointer = (event.x_root, event.y_root)

        if self.pointer_root is None:
            self.pointer_root = pointer

        if event.state & self.BUTTON_MASK:
            scrollbars = (self.get_hscrollbar(), self.get_vscrollbar())
            scrollbars = izip(pointer, self.pointer_root, scrollbars)
            for cur, prev, scrollbar in scrollbars:
                #adj = scrollbar.get_adjustment()
                value = scrollbar.get_value() + (prev - cur)
                #value = min(adj.get_upper(), max(adj.get_lower(), value))
                scrollbar.set_value(value)
            ret = True

        self.pointer_root = pointer
        return ret

    def scroll_event(self, _, event):
        direction = get_scroll_direction(event)
        #if event.state & gdk.CONTROL_MASK:
        #    if direction == ScrollDirection.UP:
        #        self.rotate += 0.1
        #    elif direction == ScrollDirection.DOWN:
        #        self.rotate -= 0.1
        #    return True
        if direction == ScrollDirection.UP:
            self.zoom_in()
        elif direction == ScrollDirection.DOWN:
            self.zoom_out()
        return True

    def zoom_in(self, *_):
        self.fit = self.FIT_NONE
        self.scale *= 1.1

    def zoom_out(self, *_):
        self.fit = self.FIT_NONE
        self.scale *= 0.9

    def zoom_fit_or_1to1(self, *_):
        if all(size < wnd for size, wnd in izip(self.size, self.window_size)):
            self.scale = 1
        else:
            self.zoom_fit()

        self.fit = self.FIT_OR_1TO1

    def zoom_fit(self, *_):
        img_width, img_height = self.size
        if img_width == 0 or img_height == 0:
            return
        width, height = self.window_size

        if width / img_width < height / img_height:
            self.zoom_fit_width()
        else:
            self.zoom_fit_height()

        self.fit = self.FIT

    def zoom_fit_width(self, *_):
        img_width, img_height = self.size
        if img_width == 0 or img_height == 0:
            return
        width, height = self.window_size

        _, policy = self.get_policy()

        if policy == PolicyType.ALWAYS:
            scrollbar = True
        else:
            scale = (width - self._fit_offset) / img_width
            scrollbar = (policy == PolicyType.AUTOMATIC \
                         and ceil(img_height * scale) >= height)

        if scrollbar:
            scale = width - self._scrollbar_size - self._fit_offset
            scale /= img_width

        self.scale = scale
        self.fit = self.FIT_WIDTH

    def zoom_fit_height(self, *_):
        img_width, img_height = self.size
        if img_width == 0 or img_height == 0:
            return

        width, height = self.window_size

        policy, _ = self.get_policy()

        if policy == PolicyType.ALWAYS:
            scrollbar = True
        else:
            scale = (height - self._fit_offset) / img_height
            scrollbar = (policy == PolicyType.AUTOMATIC \
                         and ceil(img_width * scale) >= width)

        if scrollbar:
            scale = height - self._scrollbar_size - self._fit_offset
            scale /= img_height

        self.scale = scale
        self.fit = self.FIT_HEIGHT

    def render(self, ctx):
        if self.draw_func is not None:
            self.draw_func(ctx)


class ImageWindow(DrawingWindow):

    MIN_ANIMATION_DELAY = 10

    if PYGTK:
        EVENTS = DrawingWindow.EVENTS | gdk.STRUCTURE_MASK
    else:
        EVENTS = DrawingWindow.EVENTS | gdk.EventMask.STRUCTURE_MASK

    def __init__(self,
                 image=None,
                 image_filter=cairo.FILTER_NEAREST,
                 new_image_fit=DrawingWindow.FIT_OR_1TO1):
        super(ImageWindow, self).__init__()

        self._image = None
        self._animation_timeout = None
        self._animation = None
        self._prev_delay = -1

        self.image_filter = image_filter
        self.new_image_fit = new_image_fit

        self.image = image

        #self.screen.add_events(gdk.STRUCTURE_MASK)
        self.screen.connect('map_event', print_('map', self.animate))
        self.screen.connect('unmap_event', print_('unmap', self.stop))
        self.screen.connect('destroy', print_('destroy', self.stop))

    @property
    def image(self):
        return self._image

    @image.setter
    def image(self, img):
        self.stop()

        img = load_image(img, self)
        size = get_image_size(img)
        self._image = img
        self.size = size

        self.rotate = 0.0
        self.scale = 1.0

        if self.new_image_fit != self.FIT_LAST:
            self.fit = self.new_image_fit

        self.queue_draw()
        self.animate()

    def animate(self, *_):
        self.stop()
        if isinstance(self.image, PixbufAnimation):
            self._prev_delay = -1
            self._animation = self.image.get_iter()
            self._animation_timeout = gobject.timeout_add(
                0,
                self.animation_step
            )

    def stop(self, *_):
        if self._animation_timeout is not None:
            gobject.source_remove(self._animation_timeout)
            self._prev_delay = -1
            self._animation = None
            self._animation_timeout = None

    def animation_step(self):
        if self._animation is None or self.get_window() is None:
            self._animation_timeout = None
            return False

        self._animation.advance()
        self.screen.queue_draw()

        delay = self._animation.get_delay_time()
        if delay < 0:
            self._animation_timeout = None
            return False
        delay = max(self.MIN_ANIMATION_DELAY, delay)
        #print(delay, self._prev_delay)
        if abs(delay - self._prev_delay) < 10:
            return True

        self._prev_delay = delay
        self._animation_timeout = gobject.timeout_add(
            delay,
            self.animation_step
        )
        return False

    def render(self, ctx):
        img = self.image

        if img is None:
            return

        if isinstance(img, rsvg.Handle):
            img.render_cairo(ctx)
            return

        if isinstance(img, PixbufAnimation):
            img = self._animation.get_pixbuf()

        if isinstance(img, Pixbuf):
            cairo_set_source_pixbuf(ctx, img, 0, 0)
            ctx.get_source().set_filter(self.image_filter)
            ctx.paint()
            return

        self.image = gtk_image_new_from_stock(gtk.STOCK_MISSING_IMAGE,
                                              gtk.IconSize.DIALOG)
        raise ValueError('Invalid image: ' + str(img))


def nop(*_):
    pass

def print_(msg, func):
    def ret(*args, **kwargs):
        print(msg)
        return func(*args, **kwargs)
    return ret

@contextmanager
def freeze(widget):
    window = widget.get_window()
    if window is not None:
        window.freeze_updates()
    yield
    if window is not None:
        window.thaw_updates()

def get_scroll_direction(event):
    if event.direction == ScrollDirection.SMOOTH:
        if event.delta_y < -0.01:
            return ScrollDirection.UP
        if event.delta_y > 0.01:
            return ScrollDirection.DOWN
    return event.direction

def get_pixbuf_size(pixbuf):
    return (pixbuf.get_width(), pixbuf.get_height())

def get_gtk_image_size(img):
    dtype = img.get_storage_type()

    if dtype == ImageType.EMPTY:
        return (0, 0)
    if dtype == ImageType.PIXBUF:
        return get_pixbuf_size(img.get_pixbuf())
    if dtype == ImageType.ANIMATION:
        return get_pixbuf_size(img.get_animation())
    if dtype == ImageType.STOCK:
        return gtk.icon_size_lookup(img.get_stock()[1])
    if dtype == ImageType.ICON_SET:
        return gtk.icon_size_lookup(img.get_icon_set()[1])

    #if PYGTK:
    #    if dtype == ImageType.IMAGE:
    #        img, mask = img.get_image()
    #        if img is not None:
    #            return (img.get_width(), img.get_height())
    #        if mask is not None:
    #            return mask.get_size()
    #        return (0, 0)
    #    if dtype == ImageType.PIXMAP:
    #        img, mask = img.get_pixmap()
    #        if img is not None:
    #            return img.get_size()
    #        if mask is not None:
    #            return mask.get_size()
    #        return (0, 0)

    raise ValueError('Unknown image type: ' + str(dtype))

def get_image_size(img):
    if img is None:
        return (0, 0)

    if isinstance(img, rsvg.Handle):
        return (img.get_property('width'), img.get_property('height'))

    if isinstance(img, (Pixbuf, PixbufAnimation)):
        return get_pixbuf_size(img)

    if isinstance(img, gtk.Image):
        return get_gtk_image_size(img)

    raise ValueError('Unknown image type: ' + str(img))

def load_image_file(path):
    try:
        return rsvg_handle_new_from_file(path)
    except glib.GError:
        return gtk_image_new_from_file(path)

def load_gtk_image(img, widget=None):
    dtype = img.get_storage_type()

    if dtype == ImageType.EMPTY:
        return None

    if dtype == ImageType.PIXBUF:
        return img.get_pixbuf()

    if dtype == ImageType.ANIMATION:
        return img.get_animation()

    if dtype == ImageType.STOCK:
        create_widget = widget is None
        if create_widget:
            widget = gtk.Label()
        try:
            name, size = img.get_stock()
            return widget.render_icon(name, size)
        finally:
            if create_widget:
                widget.destroy()

    raise ValueError('Unknown image type: ' + str(dtype))

def load_image(img, widget=None):
    if isinstance(img, STRING_TYPES):
        img = load_image_file(img)

    if isinstance(img, gtk.Image):
        img = load_gtk_image(img, widget)

    if isinstance(img, PixbufAnimation) and img.is_static_image():
        img = img.get_static_image()

    return img
