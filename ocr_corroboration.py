"""Local image-only second opinion; agreement is not a correctness guarantee."""
import io
import subprocess
from PIL import ImageOps
from stage_ocr import line_crop


def recognize_line(image,row):
    crop=line_crop(image,row,scale=2).convert('L')
    if crop.getpixel((0,0))<128:
        crop=ImageOps.invert(crop)
        # Normalize inverted gray backgrounds before adding a white border.
        crop=ImageOps.autocontrast(crop)
    crop=ImageOps.expand(crop,border=10,fill='white')
    data=io.BytesIO();crop.save(data,format='PNG')
    result=subprocess.run(['tesseract','stdin','stdout','-l','eng','--psm','7'],
                          input=data.getvalue(),capture_output=True,check=True,timeout=10)
    return result.stdout.decode('utf-8').strip()
