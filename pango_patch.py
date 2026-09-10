"""Optional system-Python Pango renderer. Plain text via stdin, no desktop or network."""
import base64
import io
import json
import sys
import gi
gi.require_version('Pango','1.0')
gi.require_version('PangoCairo','1.0')
from gi.repository import Pango,PangoCairo
import cairo


def render_patch(text,width,height,foreground=(15,20,25),minimum_font_size=None,maximum_font_size=None,measure_only=False,pixel_scale=1):
    if type(pixel_scale) not in (int,float) or not .5<=pixel_scale<=4:
        raise ValueError('Invalid pixel scale')
    if not isinstance(text,str) or len(text)>10000 or '\0' in text:
        raise ValueError('Invalid text')
    text.encode('utf-8')
    if any(type(n) is not int or not 1<=n<=4096 for n in (width,height)):
        raise ValueError('Invalid size')
    if len(foreground)!=3 or any(type(n) is not int or not 0<=n<=255 for n in foreground):
        raise ValueError('Invalid foreground')
    if minimum_font_size is not None and (type(minimum_font_size) is not int or not 7<=minimum_font_size<=24):
        raise ValueError('Invalid minimum font size')
    if maximum_font_size is not None and (type(maximum_font_size) is not int or not 7<=maximum_font_size<=24):
        raise ValueError('Invalid maximum font size')
    if minimum_font_size is not None and maximum_font_size is not None and minimum_font_size>maximum_font_size:
        raise ValueError('Reversed font size range')
    if measure_only and (minimum_font_size is None or maximum_font_size is None):
        raise ValueError('Measurement requires explicit font size bounds')
    surface=cairo.ImageSurface(cairo.FORMAT_ARGB32,width,height)
    context=cairo.Context(surface)
    layout=PangoCairo.create_layout(context)
    layout.get_context().set_language(Pango.Language.from_string('ja'))
    layout.set_text(text,-1)
    layout.set_width(width*Pango.SCALE)
    layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    font=Pango.FontDescription('Noto Sans CJK JP')
    minimum=round((minimum_font_size if minimum_font_size is not None else (7 if height/pixel_scale<=16 else 12))*pixel_scale)
    minimum_height=None
    for size in range(min(round((maximum_font_size if maximum_font_size is not None else 24)*pixel_scale),height),minimum-1,-1):
        font.set_absolute_size(size*Pango.SCALE)
        layout.set_font_description(font)
        unknown=layout.get_unknown_glyphs_count()
        if unknown:return dict(shown=False,reason='missing glyph',unknown_glyphs=unknown)
        ink,logical=layout.get_pixel_extents()
        dx=max(0,-ink.x)
        if ink.x+dx+ink.width>width or ink.height>height or logical.width>width:
            continue
        if measure_only:
            needed=max(size,ink.height)
            minimum_height=needed if minimum_height is None else min(minimum_height,needed)
            continue
        context.set_source_rgb(*(v/255 for v in foreground))
        context.move_to(dx,-ink.y)
        PangoCairo.show_layout(context,layout)
        data=io.BytesIO();surface.write_to_png(data)
        return dict(shown=True,font_size=size,unknown_glyphs=0,
                    ink=[ink.x+dx,0,ink.width,ink.height],
                    png=base64.b64encode(data.getvalue()).decode())
    if measure_only and minimum_height is not None:
        return dict(shown=True,minimum_height=minimum_height)
    return dict(shown=False,reason='does not fit')


if __name__=='__main__':
    request=json.loads(sys.stdin.read(2000000))
    if isinstance(request,list):
        if len(request)>32:raise ValueError('Too many patches')
        print(json.dumps([render_patch(**row) for row in request]))
    else:
        print(json.dumps(render_patch(**request)))
