from typing import BinaryIO
from pathlib import Path
import json

from ..utils import buffered_copy

ROOT_PATH = Path(__file__)


def pack_img1(stream: BinaryIO, directory: Path):
    if not directory.is_dir():
        raise ValueError("path is not a directory")

    body_length = (directory / "body.bin").stat().st_size
    cert_length = (directory / "cert.bin").stat().st_size

    with open(directory / "head.json", "r", encoding="utf-8") as head_stream:
        header_data = json.load(head_stream)

    stream.write(header_data["magic"].encode("ascii"))
    stream.write(header_data["version"].encode("ascii"))
    stream.write(bytes([header_data["signature_format"]]))
    stream.write(int.to_bytes(header_data["entry_point"], 4, "little"))
    stream.write(int.to_bytes(body_length, 4, "little"))
    stream.write(int.to_bytes(body_length + cert_length + 0x80, 4, "little"))
    stream.write(int.to_bytes(body_length + 0x80, 4, "little"))
    stream.write(int.to_bytes(cert_length, 4, "little"))
    stream.write(int.to_bytes(header_data["salt"], 32, "little"))
    stream.write(int.to_bytes(header_data["unk0"], 2, "little"))
    stream.write(int.to_bytes(header_data["unk1"], 2, "little"))
    stream.write(int.to_bytes(header_data["header_signature"], 16, "little"))
    stream.write(int.to_bytes(header_data["header_leftover"], 4, "little"))

    stream.write(bytes(0x400 - 0x54))  # change to 600 for other SoC

    with open(directory / "body.bin", "rb") as body_stream:
        if body_length > 0x1000000:
            # for files larger than 16 MB use chunked copying
            buffered_copy(
                source=body_stream,
                destination=stream,
                limit=body_length
            )
        else:
            stream.write(body_stream.read(body_length))

    with open(directory / "sign.bin", "rb") as sign_stream:
        stream.write(sign_stream.read(0x80))

    with open(directory / "cert.bin", "rb") as cert_stream:
        stream.write(cert_stream.read(cert_length))

    stream.write(bytes(0x800))
