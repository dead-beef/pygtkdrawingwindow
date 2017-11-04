import pygtk
pygtk.require('2.0')
import glib
import gtk
import cairo

from math import ceil, sin, cos
from itertools import izip, product
from threading import Thread, Lock
from time import sleep


class NoRsvg(object): # pylint:disable=too-few-public-methods
    class Handle(object): # pylint:disable=too-few-public-methods
        def __init__(self, *args, **kwargs): # pylint:disable=unused-argument
            raise glib.GError('no rsvg')

try:
    import rsvg
except ImportError:
    rsvg = NoRsvg # pylint:disable=invalid-name


class DrawingWindow(gtk.ScrolledWindow):

    FIT_LAST = -1
    FIT_NONE = 0
    FIT = 1
    FIT_WIDTH = 2
    FIT_HEIGHT = 3
    FIT_OR_1TO1 = 4

    def __init__(self, fit=FIT_OR_1TO1, draw=None):
        super(DrawingWindow, self).__init__()
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.set_shadow_type(gtk.SHADOW_NONE)

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

        self.screen.set_events(
            gtk.gdk.POINTER_MOTION_MASK |
            gtk.gdk.POINTER_MOTION_HINT_MASK |
            gtk.gdk.LEAVE_NOTIFY_MASK |
            gtk.gdk.BUTTON_PRESS_MASK |
            gtk.gdk.BUTTON_MOTION_MASK
        )
        #self.screen.set_double_buffered(False)
        self.connect('size_allocate', self.update_fit)
        self.screen.connect('expose_event', self.expose_event)
        self.screen.connect('scroll_event', self.scroll_event)
        self.screen.connect('size_allocate', self.size_allocate_event)
        self.screen.connect('motion_notify_event', self.motion_notify_event)
        self.screen.connect('leave_notify_event', self.leave_notify_event)

    @property
    def scale(self):
        return self._scale

    @scale.setter
    def scale(self, scale):
        scale = float(scale)
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
            adj = scrollbar.get_adjustment()
            value = scrollbar.get_value() + dscale * x
            value = min(adj.upper, max(adj.lower, value))
            scrollbar.set_value(value)

        self._prev_scale = None

    def update_fit(self, *_):
        try:
            self._fit[self.fit]()
        except IndexError:
            self.fit = self.FIT_NONE
            raise

    def size_allocate_event(self, *_):
        if self.screen.window is not None:
            self.screen.window.freeze_updates()
        try:
            self._zoom_scroll()
            self.update_fit()
        finally:
            if self.screen.window is not None:
                self.screen.window.thaw_updates()

    def expose_event(self, _, event):
        ctx = self.screen.window.cairo_create()

        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()

        width, height = self.size
        width *= 0.5
        height *= 0.5
        size = self.screen.window.get_size()
        off = [max(0, (wnd_size - img_size * self.scale) / 2)
               for wnd_size, img_size in izip(size, self.size)]

        ctx.identity_matrix()
        ctx.translate(*off)
        ctx.scale(self.scale, self.scale)
        ctx.translate(width, height)
        ctx.rotate(self.rotate)
        ctx.translate(-width, -height)

        self.draw(ctx)

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

        if event.state & (gtk.gdk.BUTTON2_MASK | gtk.gdk.BUTTON1_MASK):
            scrollbars = (self.get_hscrollbar(), self.get_vscrollbar())
            scrollbars = izip(pointer, self.pointer_root, scrollbars)
            for cur, prev, scrollbar in scrollbars:
                adj = scrollbar.get_adjustment()
                value = scrollbar.get_value() + (prev - cur)
                value = min(adj.upper, max(adj.lower, value))
                scrollbar.set_value(value)
            ret = True

        self.pointer_root = pointer
        return ret

    def scroll_event(self, _, event):
        #if event.state & gtk.gdk.CONTROL_MASK:
        #    if event.direction == gtk.gdk.SCROLL_UP:
        #        self.rotate += 0.1
        #    elif event.direction == gtk.gdk.SCROLL_DOWN:
        #        self.rotate -= 0.1
        #    return True
        if event.direction == gtk.gdk.SCROLL_UP:
            self.zoom_in()
        elif event.direction == gtk.gdk.SCROLL_DOWN:
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

        if float(width) / img_width < float(height) / img_height:
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

        if policy == gtk.POLICY_ALWAYS:
            scrollbar = True
        else:
            scale = float(width - self._fit_offset) / img_width
            scrollbar = (policy == gtk.POLICY_AUTOMATIC \
                         and ceil(img_height * scale) >= height)

        if scrollbar:
            scale = float(width - self._scrollbar_size - self._fit_offset)
            scale /= img_width

        self.scale = scale
        self.fit = self.FIT_WIDTH

    def zoom_fit_height(self, *_):
        img_width, img_height = self.size
        if img_width == 0 or img_height == 0:
            return

        width, height = self.window_size

        policy, _ = self.get_policy()

        if policy == gtk.POLICY_ALWAYS:
            scrollbar = True
        else:
            scale = float(height - self._fit_offset) / img_height
            scrollbar = (policy == gtk.POLICY_AUTOMATIC \
                         and ceil(img_width * scale) >= width)

        if scrollbar:
            scale = float(height - self._scrollbar_size - self._fit_offset)
            scale /= img_height

        self.scale = scale
        self.fit = self.FIT_HEIGHT

    def draw(self, ctx):
        if self.draw_func is not None:
            self.draw_func(ctx)


class ImageWindow(DrawingWindow):

    MIN_ANIMATION_DELAY = 0.01
    MAX_ANIMATION_DELAY = 0.5

    def __init__(self,
                 image=None,
                 image_filter=cairo.FILTER_GAUSSIAN,
                 new_image_fit=DrawingWindow.FIT_OR_1TO1):
        super(ImageWindow, self).__init__()

        self._image = None
        self._animation_thread = None
        self._animation = None
        self._lock = Lock()

        self.image_filter = image_filter
        self.new_image_fit = new_image_fit

        self.image = image

        self.screen.add_events(gtk.gdk.STRUCTURE_MASK)
        self.screen.connect('map_event', self.animate)
        #self.screen.connect('unmap_event', self.stop)

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
        if isinstance(self.image, gtk.gdk.PixbufAnimation):
            self._animation = self.image.get_iter()
            self._animation_thread = Thread(target=self.animation_thread)
        else:
            self._animation = None
            self._animation_thread = None

        if self._animation_thread is not None:
            self._animation_thread.start()

    def stop(self, *_):
        with self._lock:
            if self._animation_thread is not None:
                self._animation = None
        if self._animation_thread is not None:
            self._animation_thread.join()

    def animation_thread(self):
        while True:
            with gtk.gdk.lock, self._lock:
                if self._animation is None:
                    return
                if self.window is None: ##
                    return
                self._animation.advance()
                delay = self._animation.get_delay_time()
                self.screen.queue_draw()

            if delay < 0:
                return

            delay = min(self.MAX_ANIMATION_DELAY,
                        max(self.MIN_ANIMATION_DELAY, delay / 1000.0))
            sleep(delay)

    def draw(self, ctx):
        if self.image is None:
            return

        if isinstance(self.image, gtk.gdk.PixbufAnimation):
            with self._lock:
                pixbuf = self._animation.get_pixbuf()
            ctx.set_source_pixbuf(pixbuf, 0, 0)
            ctx.get_source().set_filter(self.image_filter)
            ctx.paint()
        elif isinstance(self.image, gtk.gdk.Pixbuf):
            ctx.set_source_pixbuf(self.image, 0, 0)
            ctx.get_source().set_filter(self.image_filter)
            ctx.paint()
        elif isinstance(self.image, rsvg.Handle):
            self.image.render_cairo(ctx)
        else:
            err = ValueError('Invalid image: ' + str(self.image))
            img = gtk.image_new_from_stock(gtk.STOCK_MISSING_IMAGE,
                                           gtk.ICON_SIZE_DIALOG)
            self.image = img
            raise err


def nop(*_):
    pass

def get_pixbuf_size(pixbuf):
    return (pixbuf.get_width(), pixbuf.get_height())

def get_gtk_image_size(img):
    dtype = img.get_storage_type()

    if dtype == gtk.IMAGE_EMPTY:
        return (0, 0)

    if dtype == gtk.IMAGE_PIXBUF:
        return get_pixbuf_size(img.get_pixbuf())

    if dtype == gtk.IMAGE_ANIMATION:
        return get_pixbuf_size(img.get_animation())

    if dtype == gtk.IMAGE_IMAGE:
        img, mask = img.get_image()
        if img is not None:
            return (img.get_width(), img.get_height())
        if mask is not None:
            return mask.get_size()
        return (0, 0)

    if dtype == gtk.IMAGE_PIXMAP:
        img, mask = img.get_pixmap()
        if img is not None:
            return img.get_size()
        if mask is not None:
            return mask.get_size()
        return (0, 0)

    if dtype == gtk.IMAGE_STOCK:
        _, size = img.get_stock()
        return gtk.icon_size_lookup(size)

    if dtype == gtk.IMAGE_ICON_SET:
        _, size = img.get_icon_set()
        return gtk.icon_size_lookup(size)

    raise ValueError('Unknown image type: ' + str(dtype))

def get_image_size(img):
    if img is None:
        return (0, 0)

    if isinstance(img, rsvg.Handle):
        return img.get_dimension_data()[:2]

    if isinstance(img, (gtk.gdk.Pixbuf, gtk.gdk.PixbufAnimation)):
        return get_pixbuf_size(img)

    if isinstance(img, gtk.Image):
        return get_gtk_image_size(img)

    raise ValueError('Unknown image type: ' + str(img))

def load_image(img, widget=None):
    if isinstance(img, (str, unicode)):
        try:
            img = rsvg.Handle(img)
        except glib.GError:
            img = gtk.image_new_from_file(img)

    if isinstance(img, gtk.Image):
        dtype = img.get_storage_type()
        if dtype == gtk.IMAGE_EMPTY:
            img = None
        elif dtype == gtk.IMAGE_PIXBUF:
            img = img.get_pixbuf()
        elif dtype == gtk.IMAGE_ANIMATION:
            img = img.get_animation()
        elif dtype == gtk.IMAGE_STOCK:
            create_widget = widget is None
            if create_widget:
                widget = gtk.Label()
            try:
                name, size = img.get_stock()
                img = widget.render_icon(name, size)
            finally:
                if create_widget:
                    widget.destroy()
        else:
            raise ValueError('Unknown image type: ' + str(dtype))

    if isinstance(img, gtk.gdk.PixbufAnimation) and img.is_static_image():
        img = img.get_static_image()

    return img
