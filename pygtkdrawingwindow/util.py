from __future__ import division, print_function, absolute_import, with_statement

from functools import wraps
from contextlib import contextmanager

from .deps import (
    STRING_TYPES, IntEnum, ImageType, ScrollDirection, TimeVal,
    Pixbuf, PixbufAnimation, gtk, glib, rsvg,
    rsvg_handle_new_from_file,
    gtk_image_new_from_file
)


class FitType(IntEnum):
    """Zoom fit types.
    """
    LAST = -1
    NONE = 0
    FIT = 1
    WIDTH = 2
    HEIGHT = 3
    FIT_OR_1TO1 = 4


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
