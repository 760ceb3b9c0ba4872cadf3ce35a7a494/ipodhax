from __future__ import annotations
from typing import BinaryIO
from dataclasses import dataclass
from pathlib import Path
import io

from PIL import Image

from ..utils import pixel_fromBGRA, pixels_from565


@dataclass
class FileReference:
    id: int
    offset: int
    size: int


def unpack_silverdb(stream: BinaryIO, directory: Path):
    if stream.read(4) != b"\x03\x00\x00\x00":
        raise ValueError("invalid magic")
    code_page = int.from_bytes(stream.read(4), "little")
    table_type = int.from_bytes(stream.read(4), "little")  # 1 for image, 2 (or 3?) for language
    table_type_str = stream.read(4).decode("ascii")  # paMB for image, mTDL for language
    file_count = int.from_bytes(stream.read(4), "little")
    unk0 = int.from_bytes(stream.read(4), "little")
    unk1 = int.from_bytes(stream.read(4), "little")

    print(f"{code_page=} {table_type=} {table_type_str=}")
    print(f"{file_count=} {unk0=} {unk1=}")

    if table_type_str == "paMB":
        files = []
        for file_index in range(file_count):
            files.append(FileReference(
                id=int.from_bytes(stream.read(4), "little"),
                offset=int.from_bytes(stream.read(4), "little"),
                size=int.from_bytes(stream.read(4), "little")
            ))
        ref_end_offset = stream.tell()
        print(f"{ref_end_offset=}")
        print(files)

        # apparently they give you some files with offset=0 size=0?

        unfiltered_types = set()

        for file in files:
            offset = ref_end_offset + file.offset
            print(f"{offset=}")
            stream.seek(offset)

            image_format = int.from_bytes(stream.read(2), "little")
            file_unk0 = int.from_bytes(stream.read(2), "little")  # always 1
            row_length = int.from_bytes(stream.read(2), "little")
            flags = int.from_bytes(stream.read(2), "little")
            file_unk1 = int.from_bytes(stream.read(4), "little")  # always 0
            file_unk2 = int.from_bytes(stream.read(4), "little")  # always 0
            height = int.from_bytes(stream.read(4), "little")
            width = int.from_bytes(stream.read(4), "little")
            file_id = int.from_bytes(stream.read(4), "little")  # this should match the earlier ID
            file_size = int.from_bytes(stream.read(4), "little")  # this should match the earlier size + 32 to account for header

            file_accounted_for_size = file_size + 32
            should_skip = False

            print(f"{file_id=}")
            print(f"\timage_format: 0x{image_format:04x} == 0b{image_format:016b}")

            # if image_format == 0x0565 and width == 240 and height == 240:
            #     print(f"OK! TAKE THIS! {stream.tell()}")

            print(f"\tflags: 0x{flags:04x} == 0b{flags:016b}")
            print(f"\trow_length: {row_length}")
            print(f"\tdimensions: {width}x{height}")
            print(f"\tsize: {file_size}")
            print(f"\tfile: {file}")
            print(f"\t{file_unk0=} {file_unk1=} {file_unk2=}")

            if file.id != file_id:
                should_skip = True
                print(f"\t!!! id does not match! {file.id=}")
            if file.size != file_accounted_for_size:
                should_skip = True
                print(f"\t!!! size does not match! {file.size=}")

                if file.size == 0:
                    (directory / f"{file.id}_empty.bin").touch()

            if should_skip:
                continue

            # with open(OUT_PATH / f"{file.id}_{image_format:04x}.bin", "wb") as file_stream:
            #     file_stream.write(image_data)

            pixels = []
            file_stream = io.BytesIO(stream.read(file_size))  # lazy

            greyscale = False
            data_width = width

            if image_format == 0x1888:
                # BGRA, big endian
                for _ in range((row_length // 4) * height):
                    pixels.append(pixel_fromBGRA(file_stream))

            elif image_format == 0x0004:
                # 4-bit greyscale, might be inverted?
                greyscale = True
                data_width = row_length * 2
                for _ in range(row_length * height):
                    data = file_stream.read(1)[0]
                    pixels.append(17 * (data >> 4))
                    pixels.append(17 * (data & 0b1111))

            elif image_format == 0x0008:
                # 8-bit greyscale, might be inverted?
                greyscale = True
                data_width = row_length
                for _ in range(row_length * height):
                    pixels.append(file_stream.read(1)[0])

            elif image_format == 0x0565:
                # RGB565, not supported by Pillow
                data_width = row_length // 2
                pixels = pixels_from565(file_stream, (row_length // 2 * height) * 2)

            elif image_format == 0x0064:
                # hack: palette does not support BGRA so we can't use .raw
                palette_length = int.from_bytes(file_stream.read(4), "little")
                palette = []
                for _ in range(palette_length):
                    palette.append(pixel_fromBGRA(file_stream))

                for _ in range(row_length * height):
                    index = file_stream.read(1)[0]
                    pixels.append(palette[index])

            elif image_format == 0x0065:
                palette_length = int.from_bytes(file_stream.read(4), "little")
                palette = []

                for _ in range(palette_length):
                    palette.append(pixel_fromBGRA(file_stream))

                for _ in range((row_length // 2) * height):
                    index = int.from_bytes(file_stream.read(2), "little")
                    pixels.append(palette[index])
            else:
                unfiltered_types.add(image_format)

            image = Image.new(
                mode="L" if greyscale else "RGBA",
                size=(data_width, height)
            )
            image.putdata(pixels)

            if data_width != width:
                image = image.crop((0, 0, width, height))

            image.save(directory / f"{file.id}_{image_format:04x}.png", "png")

        if len(unfiltered_types) > 0:
            print(f"left unfiltered: {unfiltered_types}")
    elif table_type_str == "mTDL":
        # apparently one file with ID 1400140320 always?
        pass
