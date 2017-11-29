from __future__ import division, print_function

import sys

from time import time
from functools import wraps
from contextlib import contextmanager
from enum import IntEnum

import cairo

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

try:
    if 'gi' in sys.modules:
        raise ImportError('use gi')

    import pygtk
    pygtk.require('2.0')
    import glib
    import gobject
    import gtk
    from gtk import gdk
    from gtk.gdk import Pixbuf, PixbufAnimation # pylint:disable=import-error

    TimeVal = None

    try:
        import rsvg # pylint:disable=import-error
    except ImportError:
        rsvg = NoRsvg

    PYGTK = True
except ImportError:
    from gi.repository import ( # pylint:disable=no-name-in-module
        Gtk as gtk,
        Gdk as gdk,
        GLib as glib,
        GObject as gobject
    )
    from gi.repository.Gtk import ImageType, PolicyType, IconSize
    from gi.repository.Gdk import ScrollDirection
    from gi.repository.GdkPixbuf import Pixbuf, PixbufAnimation

    try:
        from gi.repository.GLib import TimeVal # pylint:disable=import-error,no-name-in-module
    except ImportError:
        TimeVal = None

    try:
        from gi.repository import Rsvg as rsvg
    except ImportError:
        rsvg = NoRsvg

    PYGTK = False


from math import ceil, sin, cos
from itertools import product

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


class FitType(IntEnum):
    """Zoom fit types.
    """
    LAST = -1
    NONE = 0
    FIT = 1
    WIDTH = 2
    HEIGHT = 3
    FIT_OR_1TO1 = 4


class DrawingWindow(gtk.ScrolledWindow):
    """Drawing widget.

    Attributes
    ----------
    __gsignals__
        GObject signals:

        render(widget : `DrawingWindow`, ctx: `cairo.Context`)
            Image draw signal.
    screen : `gtk.DrawingArea`
        Drawing area.
    pointer : (`float`, `float`) or None
        Pointer coordinates on drawing area.
    pointer_root : (`float`, `float`) or None
        Pointer coordinates on root window.
    _scrollbar_size : `int`
        Scrollbar size.
    _fit_offset : `int`
        Fit offset.
    _size : (`int`, `int`)
        Image size.
    _rotate : `float`
        Image rotation angle.
    _scale : `float`
        Zoom ratio.
    _prev_scale : `float`
        Previous zoom ratio.
    _fit : `FitType`
        Fit type.
    _do_fit : `function`
        Fit function.
    _do_fit_funcs : `tuple` of `function`
        Fit functions by type.

    Examples
    --------
    >>> def render(widget, ctx):
    ...     width, height = widget.get_size()
    ...     ctx.set_source_rgb(1.0, 0.5, 1.0)
    ...     ctx.rectangle(0, 0, width, height)
    ...     ctx.stroke()
    ...
    >>> widget = DrawingWindow()
    >>> widget.set_size(200, 200)
    >>> widget.connect('render', render)
    """
    __gsignals__ = {
        'render': (gobject.SIGNAL_RUN_FIRST,
                   gobject.TYPE_NONE,
                   (gobject.TYPE_PYOBJECT,))
    }

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
        """`PolicyType` : Scrollbar policy type.
        """
        SHADOW = gtk.ShadowType.NONE
        """`ShadowType` : Shadow type.
        """
        EVENTS = gdk.EventMask.POINTER_MOTION_MASK \
                 | gdk.EventMask.POINTER_MOTION_HINT_MASK \
                 | gdk.EventMask.LEAVE_NOTIFY_MASK \
                 | gdk.EventMask.BUTTON_PRESS_MASK \
                 | gdk.EventMask.BUTTON_MOTION_MASK
        """`EventMask` : Drawing area event mask.
        """
        BUTTON_MASK = gdk.ModifierType.BUTTON2_MASK \
                      | gdk.ModifierType.BUTTON1_MASK
        """`ModifierType` : Pointer motion button mask.
        """

    def __init__(self):
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
        self._fit = None
        self._do_fit = None
        self._rotate = 0.0

        self._do_fit_funcs = (
            nop,
            self.zoom_fit,
            self.zoom_fit_width,
            self.zoom_fit_height,
            self.zoom_fit_or_1to1
        )

        self.pointer = None
        self.pointer_root = None

        self.set_zoom(1.0)
        self.set_fit(FitType.FIT_OR_1TO1)

        self.screen.set_events(self.EVENTS)
        self.connect('size_allocate', ignore_args(self.update_fit))
        self.connect('scroll_event', self.scroll_event)
        self.screen.connect('size_allocate', self.size_allocate_event)
        self.screen.connect('motion_notify_event', self.motion_notify_event)
        self.screen.connect('leave_notify_event', self.leave_notify_event)
        if PYGTK:
            self.screen.connect('expose_event', self.expose_event)
        else:
            self.screen.connect('draw', self.draw_event)

    def get_fit(self):
        """Get fit type.

        Returns
        -------
        `FitType`
        """
        return self._fit

    def set_fit(self, fit):
        """Set fit type.

        Parameters
        ----------
        fit : `FitType`
        """
        try:
            self._do_fit = self._do_fit_funcs[fit]
        except IndexError:
            raise ValueError('Invalid fit type: %s' % repr(fit))
        self._fit = fit

    def get_zoom(self):
        """Get zoom ratio.

        Returns
        -------
        `float`
        """
        return self._scale

    def set_zoom(self, ratio):
        """Set zoom ratio.

        Parameters
        -------
        ratio : `float`
        """
        if self._prev_scale is None:
            self._prev_scale = self._scale
        self._scale = ratio
        self._update_screen_size()

    def get_angle(self):
        """Get image rotation angle.

        Returns
        -------
        `float`
            Angle in radians.
        """
        return self._rotate

    def set_angle(self, angle):
        """Set image rotation angle.

        Parameters
        ----------
        angle : `float`
            Angle in radians.
        """
        width, height = self.get_size()
        width /= 2
        height /= 2
        rect = list(product((-width, width), (-height, height)))
        sin_, cos_ = sin(angle), cos(angle)
        for i, point in enumerate(rect):
            x, y = point
            rect[i] = (
                x * cos_ + y * sin_,
                y * cos_ - x * sin_
            )
        width = max(x for x, _ in rect) - min(x for x, _ in rect)
        height = max(y for _, y in rect) - min(y for _, y in rect)
        scale = self.get_zoom()
        self.screen.set_size_request(
            int(ceil(width * scale)),
            int(ceil(height * scale))
        )
        self.screen.queue_draw()
        self._rotate = angle

    def get_size(self):
        """Get image size.

        Returns
        -------
        (`int`, `int`)
            Image width and height.
        """
        return self._size

    def set_size(self, width, height):
        """Set image size.

        Parameters
        ----------
        width : `int`
            Image width.
        height : `int`
            Image height.
        """
        self._size = (width, height)
        self._update_screen_size()

    def get_window_size(self):
        """Get widget size.

        Returns
        -------
        (`int`, `int`)
            Widget width and height.
        """
        rect = self.get_allocation()
        return rect.width, rect.height

    def get_screen_size(self):
        """Get drawing area size.

        Returns
        -------
        (`int`, `int`)
            Drawing area width and height.
        """
        rect = self.screen.get_allocation()
        return rect.width, rect.height

    def _update_screen_size(self):
        """Resize drawing area.
        """
        self.screen.set_size_request(
            *(int(sz * self.get_zoom()) for sz in self.get_size())
        )

    def _zoom_scroll(self):
        """Update scroll after zooming.
        """
        if self._prev_scale is None:
            return

        dscale = self.get_zoom() / self._prev_scale

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
                in izip(scrollbars, scrollbar_sizes, self.get_window_size())
            )
        else:
            pointer = self.pointer
            self.pointer = tuple(x * dscale for x in pointer)

        dscale -= 1

        for x, scrollbar in izip(pointer, scrollbars):
            value = scrollbar.get_value() + dscale * x
            scrollbar.set_value(value)

        self._prev_scale = None

    def size_allocate_event(self, _, ev_):
        """Handle drawing area size allocate event.

        Parameters
        ----------
        _ : `gtk.DrawingArea`
        ev_ : `gtk.gdk.Event`
        """
        with freeze(self.screen):
            self._zoom_scroll()
            self.update_fit()

    def expose_event(self, _, event):
        """Handle drawing area expose event.

        Parameters
        ----------
        _ : `gtk.DrawingArea`
        event : `gtk.gdk.Event`
        """
        ctx = self.screen.get_window().cairo_create()
        ctx.rectangle(event.area.x, event.area.y,
                      event.area.width, event.area.height)
        ctx.clip()
        self.draw_event(None, ctx)

    def draw_event(self, _, ctx):
        """Handle drawing area draw event.

        Parameters
        ----------
        _ : `gtk.DrawingArea`
        ctx : `cairo.Context`
        """
        size = self.get_size()
        scale = self.get_zoom()
        width, height = size
        width *= 0.5
        height *= 0.5
        off = [max(0, (wnd_size - img_size * scale) / 2)
               for wnd_size, img_size in izip(self.get_screen_size(), size)]

        ctx.translate(*off)
        ctx.scale(scale, scale)
        ctx.translate(width, height)
        ctx.rotate(self.get_angle())
        ctx.translate(-width, -height)

        self.emit('render', ctx)

    def leave_notify_event(self, _, ev_):
        """Handle leave notify event.

        Parameters
        ----------
        _ : `gtk.DrawingArea`
        ev_ : `gtk.gdk.Event`

        Returns
        -------
        `bool`
            `True` to stop event propagation.
        """
        self.pointer = None
        self.pointer_root = None
        return False

    def motion_notify_event(self, _, event):
        """Handle pointer motion event.

        Parameters
        ----------
        _ : `gtk.DrawingArea`
        event : `gtk.gdk.Event`

        Returns
        -------
        `bool`
            `True` to stop event propagation.
        """
        ret = False

        self.pointer = (event.x, event.y)
        pointer = (event.x_root, event.y_root)

        if self.pointer_root is None:
            self.pointer_root = pointer

        if event.state & self.BUTTON_MASK:
            scrollbars = (self.get_hscrollbar(), self.get_vscrollbar())
            scrollbars = izip(pointer, self.pointer_root, scrollbars)
            for cur, prev, scrollbar in scrollbars:
                value = scrollbar.get_value() + (prev - cur)
                scrollbar.set_value(value)
            ret = True

        self.pointer_root = pointer
        return ret

    def scroll_event(self, _, event):
        """Handle scroll event.

        Parameters
        ----------
        _ : `DrawingWindow`
        event : `gtk.gdk.Event`

        Returns
        -------
        `bool`
            `True` to stop event propagation.
        """
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

    def queue_draw(self): # pylint:disable=arguments-differ
        """Queue drawing area redraw.
        """
        #super(DrawingWindow, self).queue_draw()
        self.screen.queue_draw()

    def update_fit(self):
        """Update zoom to fit resized widget.
        """
        self._do_fit()

    def zoom_in(self):
        """Zoom in.
        """
        self.set_fit(FitType.NONE)
        self.set_zoom(self.get_zoom() * 1.1)

    def zoom_out(self):
        """Zoom out.
        """
        self.set_fit(FitType.NONE)
        self.set_zoom(self.get_zoom() * 0.9)

    def zoom_fit_or_1to1(self):
        """Zoom to fit or 1:1.
        """
        if all(size < wnd
               for size, wnd
               in izip(self.get_size(), self.get_window_size())):
            self.set_zoom(1)
        else:
            self.zoom_fit()

        self.set_fit(FitType.FIT_OR_1TO1)

    def zoom_fit(self):
        """Zoom to fit width and height.
        """
        img_width, img_height = self.get_size()
        if img_width == 0 or img_height == 0:
            return
        width, height = self.get_window_size()

        if width / img_width < height / img_height:
            self.zoom_fit_width()
        else:
            self.zoom_fit_height()

        self.set_fit(FitType.FIT)

    def zoom_fit_width(self):
        """Zoom to fit width.
        """
        img_width, img_height = self.get_size()
        if img_width == 0 or img_height == 0:
            return
        width, height = self.get_window_size()

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

        self.set_zoom(scale)
        self.set_fit(FitType.WIDTH)

    def zoom_fit_height(self):
        """Zoom to fit height.
        """
        img_width, img_height = self.get_size()
        if img_width == 0 or img_height == 0:
            return

        width, height = self.get_window_size()

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

        self.set_zoom(scale)
        self.set_fit(FitType.HEIGHT)


class ImageWindow(DrawingWindow):
    """Drawing widget with background image.

    Attributes
    ----------
    image_filter
        Cairo filter for image scaling.
    new_image_fit : `FitType`
        Fit type to set on image change.
    _image : `None` or `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation` or `rsvg.Handle`
        Background image.
    _animation : `gtk.gdk.PixbufAnimationIter`
        Animation iterator.
    _animation_time : `float` or `None`
        Animation start/stop time.
    _animation_timeout : `int` or `None`
        Animation timeout id.
    _prev_delay : `int`
        Previous frame delay in milliseconds.
    """
    MIN_ANIMATION_DELAY = 10
    """`int` : Minimum animation frame delay in milliseconds.
    """

    if PYGTK:
        EVENTS = DrawingWindow.EVENTS | gdk.STRUCTURE_MASK
    else:
        EVENTS = DrawingWindow.EVENTS | gdk.EventMask.STRUCTURE_MASK
        """`EventMask` : Drawing area event mask.
        """

    def __init__(self):
        """Drawing widget constructor.
        """
        super(ImageWindow, self).__init__()

        self._image = None
        self._animation_timeout = None
        self._animation_time = None
        self._animation = None
        self._prev_delay = -1

        self.image_filter = cairo.FILTER_NEAREST
        self.new_image_fit = FitType.FIT_OR_1TO1

        start = ignore_args(self.start_animation)
        stop = ignore_args(self.stop_animation)
        self.screen.connect('map_event', log('map')(start))
        self.screen.connect('unmap_event', log('unmap')(stop))
        self.screen.connect('destroy', log('destroy')(stop))

    def get_image(self):
        """Get background image.

        Returns
        -------
        `None` or `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation` or `rsvg.Handle`
            Background image.
        """
        return self._image

    def set_image(self, img):
        """Set background image.

        Parameters
        ----------
        img : `None` or `str` or `gtk.Image` or `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation` or `rsvg.Handle`
            Background image.
        """
        self.stop_animation()

        img = load_image(img, self)
        width, height = get_image_size(img)
        self._image = img
        self.set_size(width, height)
        self.reset_animation()
        self.set_angle(0.0)
        self.set_zoom(1.0)
        if self.new_image_fit != FitType.LAST:
            self.set_fit(self.new_image_fit)

        self.queue_draw()
        self.start_animation()

    def start_animation(self):
        """Start animation.
        """
        if not self.has_animation():
            return
        self.stop_animation()
        self._prev_delay = -1
        start_time = time()
        if self._animation_time is not None:
            start = get_timeval(start_time - self._animation_time)
            self._animation = self.get_image().get_iter(start)
        self._animation_time = start_time
        self._animation_timeout = gobject.idle_add(self.animation_step)

    def stop_animation(self):
        """Stop animation.
        """
        if not self.get_animation():
            return
        gobject.source_remove(self._animation_timeout)
        self._prev_delay = -1
        self._animation_time = time() - self._animation_time
        self._animation_timeout = None

    def reset_animation(self):
        """Restart animation.
        """
        if self.has_animation():
            self._animation = self.get_image().get_iter()
            self._animation_time = time()
        else:
            self._animation = None
            self._animation_time = None

    def has_animation(self):
        """
        Returns
        -------
        `bool`
            `True` if background image is animated.
        """
        return isinstance(self.get_image(), PixbufAnimation)

    def get_animation(self):
        """
        Returns
        -------
        `bool`
            `True` if animation is started.
        """
        return self._animation_timeout is not None

    def set_animation(self, enable):
        """Set animation state.

        Parameters
        ----------
        enable : `bool`
            `True` to start animation, `False` to stop.
        """
        if enable:
            self.start_animation()
        else:
            self.stop_animation()

    def animation_step(self):
        """Animation timeout.
        """
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

    def do_render(self, ctx):
        """Handle `render` signal.

        Parameters
        ----------
        ctx : `cairo.Context`
        """
        img = self.get_image()

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

        err = gtk_image_new_from_stock(gtk.STOCK_MISSING_IMAGE, IconSize.DIALOG)
        self.set_image(err)
        #raise ValueError('Invalid image: ' + str(img))


def nop(*_, **kw_):
    """Do nothing.

    Parameters
    ----------
    *_
        Unused.
    **kw_
        Unused.
    """
    pass

def log(msg):
    """Log function calls.

    Parameters
    ----------
    msg : `str`
        Message to print before each function call.

    Returns
    -------
    `function`
        Decorator.

    Examples
    --------
    >>> @log('called')
    ... def f(x):
    ...   return x
    ...
    >>> f(0)
    called
    0
    """
    def decorator(func):
        @wraps(func)
        def ret(*args, **kwargs):
            print(msg)
            return func(*args, **kwargs)
        return ret
    return decorator

def ignore_args(func):
    """Create a function that ignores its arguments.

    Parameters
    ----------
    func : `function`
        Function to decorate.

    Returns
    -------
    `function`

    Examples
    --------
    >>> @ignore_args
    ... def f(*args):
    ...     print(args)
    ...
    >>> f(1, 2, x=3)
    ()
    """
    @wraps(func)
    def ret(*_, **kw_):
        return func()
    return ret

@contextmanager
def freeze(widget):
    """Widget update freezing context manager.

    Parameters
    ----------
    widget : `gtk.Widget`
        Widget to freeze.
    """
    window = widget.get_window()
    if window is not None:
        window.freeze_updates()
    try:
        yield
    finally:
        if window is not None:
            window.thaw_updates()

def get_scroll_direction(event):
    """Get scroll event direction.

    Parameters
    ----------
    event : `gtk.gdk.Event`
        Scroll event.

    Returns
    -------
    `ScrollDirection`
    """
    if event.direction == ScrollDirection.SMOOTH:
        if event.delta_y < -0.01:
            return ScrollDirection.UP
        if event.delta_y > 0.01:
            return ScrollDirection.DOWN
    return event.direction

def get_timeval(time_):
    """Get time value.

    Parameters
    ----------
    time_ : `float`
        Time from `time.time()`

    Returns
    -------
    `gi.repository.GLib.TimeVal` or `float`
        Time value for `gtk.gdk.PixbufAnimation.get_iter()`.
    """
    if TimeVal is None:
        return time_
    ret = TimeVal()
    ret.add(int(time_ * 1e6))
    return ret

def get_pixbuf_size(pixbuf):
    """Get GTK pixbuf size.

    Parameters
    ----------
    img: `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation`

    Returns
    -------
    (`int`, `int`)
        Pixbuf width and height.
    """
    return pixbuf.get_width(), pixbuf.get_height()

def get_gtk_image_size(img):
    """Get GTK size.

    Parameters
    ----------
    img: `gtk.Image`

    Raises
    ------
    ValueError
        If image storage type is invalid.

    Returns
    -------
    (`int`, `int`)
        Image width and height.
    """
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
    """Get image size.

    Parameters
    ----------
    img: `None` or `rsvg.Handle` or `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation` or `gtk.Image`

    Raises
    ------
    TypeError
        If image type is invalid.

    Returns
    -------
    (`int`, `int`)
        Image width and height.
    """
    if img is None:
        return (0, 0)

    if isinstance(img, rsvg.Handle):
        return (img.get_property('width'), img.get_property('height'))

    if isinstance(img, (Pixbuf, PixbufAnimation)):
        return get_pixbuf_size(img)

    if isinstance(img, gtk.Image):
        return get_gtk_image_size(img)

    raise TypeError('Invalid image type: ' + str(img))

def load_image_file(path):
    """Load image from file.

    Parameters
    ----------
    path : `str`
        Image file path.

    Returns
    -------
    `rsvg.Handle` or `gtk.Image`
        Loaded image.
    """
    try:
        return rsvg_handle_new_from_file(path)
    except glib.GError:
        return gtk_image_new_from_file(path)

def load_gtk_image(img, widget=None):
    """Load GTK image.

    Parameters
    ----------
    img : `gtk.Image`
        Image to load.
    widget : `gtk.Widget`, optional
        Widget for icon rendering (default: gtk.Label()).

    Raises
    ------
    ValueError
        If image storage type not in (EMPTY, PIXBUF, ANIMATION, STOCK).

    Returns
    -------
    `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation` or `None`
        Loaded image or `None` if image is empty.
    """
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
    """Load an image.

    Parameters
    ----------
    img : `str` or `gtk.Image` or `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation` or `rsvg.Handle`
        Image to load.
    widget : `gtk.Widget`, optional
        Widget for icon rendering (default: gtk.Label()).

    Returns
    -------
    `gtk.gdk.Pixbuf` or `gtk.gdk.PixbufAnimation` or `rsvg.Handle` or `None`
        Loaded image or `None` if image is empty.
    """
    if isinstance(img, STRING_TYPES):
        img = load_image_file(img)

    if isinstance(img, gtk.Image):
        img = load_gtk_image(img, widget)

    if isinstance(img, PixbufAnimation) and img.is_static_image():
        img = img.get_static_image()

    return img


gobject.type_register(DrawingWindow)
gobject.type_register(ImageWindow)
