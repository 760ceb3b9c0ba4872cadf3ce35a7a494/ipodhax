from __future__ import annotations
from typing import BinaryIO
from pathlib import Path
import math

from PIL import Image

from ..utils import pixel_toBGRA, pixel_to565

ROOT_PATH = Path(__file__).parent


def encode_image(image_id: int, image_format: int, path: Path, stream: BinaryIO):
    image: Image.Image

    with Image.open(path) as image:
        start_offset = stream.tell()

        stream.write(int.to_bytes(image_format, 2, "little"))
        stream.write(int.to_bytes(1, 2, "little"))  # unk0

        if image_format == 0x1888:
            # keep RGBA
            flags = 0x0020
            row_length = image.size[0] * 4
        elif image_format == 0x0004:
            image = image.convert("L")
            flags = 0x0004
            row_length = math.ceil(image.size[0] / 2)  # will be used later
        elif image_format == 0x0008:
            image = image.convert("L")
            flags = 0x0008
            row_length = image.size[0]
        elif image_format == 0x0565:
            image = image.convert("RGB")
            flags = 0x0010
            row_length = image.size[0] * 2
        elif image_format == 0x0064:
            # keep RGBA
            flags = 0x0008
            row_length = image.size[0]
        elif image_format == 0x0065:
            # keep RGBA
            flags = 0x0010
            row_length = image.size[0] * 2
        else:
            raise ValueError(f"cannot pack unknown format {image_format:04x}")

        stream.write(int.to_bytes(row_length, 2, "little"))
        stream.write(int.to_bytes(flags, 2, "little"))
        stream.write(bytes(4))  # unk1
        stream.write(bytes(4))  # unk2
        stream.write(int.to_bytes(image.size[1], 4, "little"))
        stream.write(int.to_bytes(image.size[0], 4, "little"))
        stream.write(int.to_bytes(image_id, 4, "little"))
        length_offset = stream.tell()  # hack: come back here to write length
        stream.write(bytes(4))
        # 32 bytes written

        # header_end_offset = stream.tell()
        if image_format == 0x1888:
            for pixel in image.getdata():
                stream.write(pixel_toBGRA(pixel))
        elif image_format == 0x0004:
            width = image.size[0]
            height = image.size[1]

            pixels = list(image.getdata())

            array = bytearray()

            for y in range(height):
                row = pixels[(y * width):((y * width) + width)]

                if len(row) % 2 != 0:
                    row.append(0)

                for x_idx in range(0, len(row), 2):
                    i0, i1 = row[x_idx:x_idx+2]
                    array.append(((i0 // 17) << 4) + (i1 // 17))
            stream.write(array)
        elif image_format == 0x0008:
            stream.write(bytes(image.getdata()))
        elif image_format == 0x0565:
            for pixel in image.getdata():
                stream.write(int.to_bytes(pixel_to565(pixel), 2, "little"))
        elif image_format in {0x0064, 0x0065}:
            pixels = image.getdata()
            unique_pixels = list(set(pixels))

            if image_format == 0x0064:
                if len(unique_pixels) > 0xFF:
                    raise ValueError(f"more than 255 colors in {image_id}")
            elif image_format == 0x0065:
                if len(unique_pixels) > 0xFFFF:
                    raise ValueError(f"more than 65535 colors in {image_id}")

            stream.write(int.to_bytes(len(unique_pixels), 4, "little"))

            for color in unique_pixels:
                stream.write(pixel_toBGRA(color))

            reverse_index = {color: n for n, color in enumerate(unique_pixels)}

            for pixel in pixels:
                stream.write(int.to_bytes(reverse_index[pixel], 1 if image_format == 0x0064 else 2, "little"))
        else:
            raise ValueError(f"unk format: 0x{image_format:04x}")

        end_offset = stream.tell()
        length = (end_offset - start_offset)
        stream.seek(length_offset)
        stream.write(int.to_bytes((length - 32), 4, "little"))  # smaller to account for head
        stream.seek(end_offset)

    return start_offset, length


def pack_silverdb(stream: BinaryIO, directory: Path):
    items = []
    for path in directory.glob("*_*.*"):
        if path.stem.startswith("."):
            continue

        image_id, image_format = path.stem.split("_")

        items.append((
            int(image_id),
            None if image_format == "empty" else int(image_format, 16)
        ))

    items.sort(key=lambda k: k[0])

    stream.write(b"\x03\x00\x00\x00")

    ref_end_offset_offset = stream.tell()
    stream.write(bytes(4))

    stream.write(int.to_bytes(1, 4, "little"))
    stream.write(b"paMB")
    stream.write(int.to_bytes(len(items), 4, "little"))
    stream.write(int.to_bytes(1, 4, "little"))
    stream.write(int.to_bytes(28, 4, "little"))

    file_info_offset = stream.tell()  # seek back here
    stream.write(bytes(len(items) * (4 * 3)))

    ref_end_offset = stream.tell()
    stream.seek(ref_end_offset_offset)
    stream.write(int.to_bytes(ref_end_offset, 4, "little"))
    stream.seek(ref_end_offset)

    file_offset_lengths = []  # fill this with tuples!

    print("writing image..")
    for image_id, image_format in items:
        if image_format:
            path = directory / f"{image_id}_{image_format:04x}.png"
            offset, length = encode_image(
                image_id=image_id,
                image_format=image_format,
                path=path,
                stream=stream
            )
            if length % 2 != 0:
                stream.write(b"\x00")  # pad to 2

            print(f"\t{image_id=} {image_format=:04x} {offset=} {length=}")
            file_offset_lengths.append((image_id, offset, length))
        else:
            print(f"\t{image_id=} empty")
            file_offset_lengths.append((
                image_id,
                stream.tell(),  # wrongly pretend.
                0
            ))

    stream.seek(file_info_offset)
    print("writing metadata...")
    print(ref_end_offset)
    for (image_id, image_offset, image_length) in file_offset_lengths:
        print(f"\t{image_id=} {image_offset=} {image_length=}")
        stream.write(int.to_bytes(image_id, 4, "little"))
        stream.write(int.to_bytes(image_offset - ref_end_offset, 4, "little"))
        stream.write(int.to_bytes(image_length, 4, "little"))  # account for header
