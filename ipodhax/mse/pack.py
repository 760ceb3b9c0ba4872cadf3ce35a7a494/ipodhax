from typing import BinaryIO, Literal
from pathlib import Path
import io

from ..utils import buffered_copy

ROOT_DIR = Path(__file__).parent
STOP_SIGN = rb"{{~~  /-----\   " \
            rb"{{~~ /       \  " \
            rb"{{~~|         | " \
            rb"{{~~| S T O P | " \
            rb"{{~~|         | " \
            rb"{{~~ \       /  " \
            rb"{{~~  \-----/   " \
            rb"Copyright(C) 200" \
            rb"1 Apple Computer" \
            rb", Inc.----------" \
            rb"----------------" \
            rb"----------------" \
            rb"----------------" \
            rb"----------------" \
            rb"----------------" \
            rb"---------------" b"\x00"

UNK0 = b"\x5D\x69\x68\x5B\x00\x40\x00\x00\x0C\x01\x03\x00"

TYPE_ORDER = ["disk", "diag", "fv00", "appl", "lbat", "bdsw", "bdhw", "chrg", "gpfw", "rsrc", "osos"]
# ^^ fv00 and gpfw are n7g-only

N6G_LOAD_ADDRESSES = {
    # n7g writes 0xFFFFFFFF to this field in all cases
    "disk": 0x7FDF0008,
    "diag": 0x7FD10008,
    "appl": 0x006F0668,
    "lbat": 0x006F0668,
    "bdsw": 0x006F0668,
    "bdhw": 0x006F0668,
    "chrg": 0x006F0668,
    "rsrc": 0x634b0008,
    "osos": 0x7ee50008
}

TYPES = set(TYPE_ORDER)

OFFSET = 0x5000


def pack_mse(stream: BinaryIO, directory: Path, *, device: Literal[6, 7]):
    if device not in {6, 7}:
        raise ValueError("invalid device")

    passed_image_types = [path.stem for path in directory.glob("*.img1") if not path.name.startswith(".")]

    with open(ROOT_DIR / "certificate.bin", "rb") as cert_stream:
        cert_data = cert_stream.read(2048)  # bad, not portable

    stream.write(STOP_SIGN)
    stream.write(UNK0)
    # pad to offset
    stream.write(bytes(OFFSET - stream.tell()))

    # order things the right way? (maybe unnecessary)
    image_type_order = []
    for possible_item in TYPE_ORDER:
        if possible_item in passed_image_types:
            # bad perf but who cares
            image_type_order.append(possible_item)
            passed_image_types.remove(possible_item)
    image_type_order.extend(passed_image_types)

    stream.write(bytes(0x1000))  # this will be overwritten later when we seek back to offset to write metadata

    metadata_pairs = []  # will contain (offset, length) pairs

    for image_type in image_type_order:
        # maybe this would be better if it was continuous and didn't seek around?

        file_path = directory / f"{image_type}.img1"
        with open(file_path, "rb") as file_stream:
            file_stream.seek(0, io.SEEK_END)
            file_length = file_stream.tell()
            file_stream.seek(0)

            start_offset = stream.tell()

            if file_length > 0x1000000:
                # for files larger than 16 MB use chunked copying
                buffered_copy(
                    source=file_stream,
                    destination=stream,
                    limit=file_length
                )
            else:
                stream.write(file_stream.read(file_length))

            stream.write(cert_data)

            # pad to nearest 0x1000
            end_offset = stream.tell()
            extra_bytes = 0x1000 - (end_offset % 0x1000)
            stream.write(bytes(extra_bytes))

            metadata_pairs.append((start_offset, end_offset - start_offset))

    stream.seek(OFFSET)
    for index, (offset, file_length) in enumerate(metadata_pairs):
        image_type = image_type_order[index]

        metadata_stream = bytearray()
        metadata_stream.extend("NAND".encode("ascii")[::-1])
        metadata_stream.extend(image_type.encode("ascii")[::-1])
        metadata_stream.extend(b"\x00\x00\x00\x00")  # id

        dev_offset = offset - 0x1000
        length = file_length - 0x1000
        address = 0x8000000 if image_type in {"disk", "diag", "fv00", "osos"} else 0x0
        entry_offset = 0x400 if image_type == "rsrc" else 0x0
        checksum = 0x0
        version = 0x0 if image_type == "rsrc" else 0x1e000
        load_address = N6G_LOAD_ADDRESSES[image_type] if device == 6 else 0xFFFFFFFF

        metadata_stream.extend(int.to_bytes(dev_offset, 4, "little"))
        metadata_stream.extend(int.to_bytes(length, 4, "little"))
        metadata_stream.extend(int.to_bytes(address, 4, "little"))
        metadata_stream.extend(int.to_bytes(entry_offset, 4, "little"))
        metadata_stream.extend(int.to_bytes(checksum, 4, "little"))
        metadata_stream.extend(int.to_bytes(version, 4, "little"))
        metadata_stream.extend(int.to_bytes(load_address, 4, "little"))

        stream.write(metadata_stream)

    for _ in range(16 - len(metadata_pairs)):
        stream.write((b"\x00" * 36) + (b"\xFF" * 4))
