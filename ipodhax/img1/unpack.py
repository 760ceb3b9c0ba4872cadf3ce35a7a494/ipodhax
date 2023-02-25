from typing import BinaryIO
from pathlib import Path
import json
import io

from ..utils import buffered_copy

ROOT_PATH = Path(__file__).parent


def unpack_img1(stream: BinaryIO, directory: Path):
    magic = stream.read(4).decode("ascii")
    version = stream.read(3).decode("ascii")

    if version != "2.0":
        raise ValueError("unsupported img1 version")

    signature_format = stream.read(1)[0]
    entry_point = int.from_bytes(stream.read(4), "little")  # (relative to header end)
    body_length = int.from_bytes(stream.read(4), "little")
    data_length = int.from_bytes(stream.read(4), "little")  # inferred
    footer_offset = int.from_bytes(stream.read(4), "little")  # inferred
    footer_length = int.from_bytes(stream.read(4), "little")
    salt = int.from_bytes(stream.read(32), "little")
    unk0 = int.from_bytes(stream.read(2), "little")
    unk1 = int.from_bytes(stream.read(2), "little")
    header_signature = int.from_bytes(stream.read(16), "little")
    header_leftover = int.from_bytes(stream.read(4), "little")

    r"""
    print(f"\tSoC: {magic}")
    print(f"\tVersion: {version}")
    print(f"\tSignature format: {signature_format}")
    print(f"\tEntry point: 0x{entry_point:08x}")
    print(f"\tBody length: 0x{body_length:08x}")
    print(f"\tData length: 0x{data_length:08x}")
    print(f"\tFooter offset: 0x{footer_offset:08x}")
    print(f"\tFooter length: 0x{footer_length:08x}")
    print(f"\tSalt: {salt}")
    print(f"\tunk0: {unk0}")
    print(f"\tunk1: {unk1}")
    print(f"\tHeader signature: 0x{header_signature:032x}")
    print(f"\tHeader leftover: 0x{header_leftover:08x}")
    """

    with open(directory / "head.json", "w", encoding="utf-8") as head_stream:
        json.dump({
            "magic": magic,
            "version": version,
            "signature_format": signature_format,
            "entry_point": entry_point,
            "salt": salt,
            "unk0": unk0,
            "unk1": unk1,
            "header_signature": header_signature,
            "header_leftover": header_leftover
        }, fp=head_stream, indent=2)

    stream.seek(0x400 - 0x54, io.SEEK_CUR)  # change to 600 for other SoC
    with open(directory / "body.bin", "wb") as body_stream:
        if body_length > 0x1000000:
            # for files larger than 16 MB use chunked copying
            buffered_copy(
                source=stream,
                destination=body_stream,
                limit=body_length
            )
        else:
            body_stream.write(stream.read(body_length))

    with open(directory / "sign.bin", "wb") as signature_stream:
        signature_stream.write(stream.read(0x80))  # this makes an assumption and ignores footer_offset

    # we should now be at footer offset, pretend.
    with open(directory / "cert.bin", "wb") as certificate_stream:
        certificate_stream.write(stream.read(footer_length))

    # 0x800 null bytes
