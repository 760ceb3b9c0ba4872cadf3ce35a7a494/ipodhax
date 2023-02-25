from typing import BinaryIO, Tuple, List


def buffered_copy(
    source: BinaryIO,
    destination: BinaryIO,
    *,
    limit: int = None,
    buffer_size: int = 0x1000
):
    offset = 0

    while True:
        read_amount = min(buffer_size, limit - offset) if limit else buffer_size
        buffer = source.read(read_amount)
        offset += read_amount

        destination.write(buffer)

        if len(buffer) < buffer_size:
            # either we've hit the limit or there is no more data
            break


def pixel_from565(pixel: int) -> Tuple[int, int, int]:
    return (
        int((pixel >> 11 & 0b11111) * (255 / 0b11111)),
        int((pixel >> 5 & 0b111111) * (255 / 0b111111)),
        int((pixel & 0b11111) * (255 / 0b11111))
    )


def pixel_to565(pixel: Tuple[int, int, int]) -> int:
    return (
        ((
            (int(0b11111 * (int(pixel[0]) / 255)) << 6) +
            (int(0b111111 * (int(pixel[1]) / 255)))
        ) << 5) +
        (int(0b11111 * (int(pixel[2]) / 255)))
    )


def pixels_from565(stream: BinaryIO, length: int) -> List[Tuple[int, int, int]]:
    pixels_list = []

    for index in range(length // 2):
        pixel = int.from_bytes(stream.read(2), "little")
        pixels_list.append(pixel_from565(pixel))

    return pixels_list


def pixels_from565_bytes(stream: bytes, length: int) -> List[Tuple[int, int, int]]:
    pixels_list = []

    for index in range(length // 2):
        pixel = int.from_bytes(stream[(index*2):(index*2+2)], "little")
        pixels_list.append(pixel_from565(pixel))

    return pixels_list


def pixel_toBGRA(pixel: Tuple[int, int, int, int]) -> bytes:
    return bytes([
        pixel[2],
        pixel[1],
        pixel[0],
        pixel[3]
    ])


def pixel_fromBGRA(stream: BinaryIO) -> Tuple[int, int, int, int]:
    color = stream.read(4)
    return (
        color[2],
        color[1],
        color[0],
        color[3]
    )
