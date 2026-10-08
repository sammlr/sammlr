"""Private control photos use the existing JPEG/PNG metadata sanitizers."""
import struct
from profile_sticker import _sanitise_png, _sanitise_jpeg, _jpeg_dimensions

MAX_BYTES=12*1024*1024


def sanitise(data):
    if not data or len(data)>MAX_BYTES:raise ValueError('Foto muss zwischen 1 Byte und 12 MB groß sein')
    try:
        if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data)>=24 and data[12:16]==b'IHDR':
            dimensions=struct.unpack('>II',data[16:24]);safe=_sanitise_png(data);mime,ext='image/png','png'
        elif data.startswith(b'\xff\xd8\xff'):
            dimensions=_jpeg_dimensions(data);safe=_sanitise_jpeg(data);mime,ext='image/jpeg','jpg'
        else:raise ValueError('Bitte ein JPEG- oder PNG-Foto auswählen')
        if not dimensions or min(dimensions)<1 or max(dimensions)>8000 or dimensions[0]*dimensions[1]>40_000_000:
            raise ValueError('Bildabmessungen nicht unterstützt')
        return safe,mime,ext
    except (IndexError,struct.error) as error:
        raise ValueError('Ungültige Bilddatei') from error
