from __future__ import division, print_function, absolute_import, with_statement

from math import sin, cos, ceil
from itertools import product

from .deps import (
    PYGTK, gtk, gdk, gobject, izip, PolicyType, ScrollDirection
)

from .util import FitType, nop, freeze, ignore_args, get_scroll_direction


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
        """Handle drawing area `size-allocate` event.

        Parameters
        ----------
        _ : `gtk.DrawingArea`
        ev_ : `gtk.gdk.Event`
        """
        with freeze(self.screen):
            self._zoom_scroll()
            self.update_fit()

    def expose_event(self, _, event):
        """Handle drawing area `expose` event.

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
        """Handle drawing area `draw` event.

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
        """Handle drawing area `leave-notify` event.

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
        """Handle drawing area `motion-notify` event.

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
        """Handle `scroll` event.

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


gobject.type_register(DrawingWindow)
