from __future__ import division, print_function, absolute_import, with_statement

from time import time

from .deps import (
    PYGTK, gtk, gdk, gobject, cairo, rsvg,
    Pixbuf, PixbufAnimation, IconSize,
    cairo_set_source_pixbuf,
    gtk_image_new_from_stock
)
from .util import (
    FitType, log, ignore_args,
    load_image, get_image_size, get_timeval
)
from .base import DrawingWindow


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


gobject.type_register(ImageWindow)
