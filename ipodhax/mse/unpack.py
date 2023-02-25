from dataclasses import dataclass
from typing import BinaryIO
from pathlib import Path

from ..utils import buffered_copy

OFFSET = 0x5000


@dataclass
class ImageMetadata:
    target: str  # "NAND", "NOR!", "flsh"
    type: str  # "disk", "diag", "appl", "lbat", "bdsw", "chrg", "rsrc", "osos"

    # id: int
    dev_offset: int
    length: int
    address: int

    entry_offset: int
    # checksum: int
    version: int
    load_address: int


def unpack_mse(stream: BinaryIO, directory: Path):
    stream.seek(OFFSET)

    images = []
    for image_index in range(16):
        # 16 slots
        image_data = stream.read(40)
        if image_data[0:4] == b"\x00\x00\x00\x00":
            # placeholder
            continue

        pieces = [image_data[i:i+4] for i in range(0, 40, 4)]

        image_target = pieces[0][::-1].decode("ascii")
        image_type = pieces[1][::-1].decode("ascii")

        image = ImageMetadata(
            target=image_target,
            type=image_type,
            # id=int.from_bytes(pieces[2], "little"),
            dev_offset=int.from_bytes(pieces[3], "little"),
            length=int.from_bytes(pieces[4], "little"),
            address=int.from_bytes(pieces[5], "little"),
            entry_offset=int.from_bytes(pieces[6], "little"),
            # checksum=int.from_bytes(pieces[7], "little"),
            version=int.from_bytes(pieces[8], "little"),
            load_address=int.from_bytes(pieces[9], "little"),
        )

        images.append(image)

    print(images)

    for image in images:
        print(f"extracting {image}")

        stream.seek(image.dev_offset + 0x1000)  # 4096 padding? unclear.
        read_length = image.length + 0x800  # length does not include the 0x800 img1 header overhead

        with open(directory / f"{image.type}.img1", "wb") as image_stream:
            if image.length > 0x1000000:
                # for files larger than 16 MB use chunked copying
                buffered_copy(
                    source=stream,
                    destination=image_stream,
                    limit=read_length
                )
            else:
                image_stream.write(stream.read(read_length))
