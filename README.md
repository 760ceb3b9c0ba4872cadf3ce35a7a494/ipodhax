# ipodhax
my work on iPod nano 6g and 7g pwning. right now we have no code-exec on these devices.

## MSE
MSE is a container format for multiple IMG1s, present in IPSW files with the name `Firmware.MSE`.

each IMG1 has a name. the nano 6g has `disk`, `diag`, `appl`, `lbat`, `bdsw`, `bdhw`, `chrg`, `rsrc`, and `osos`, with the 7g adding `fv00` and `gpfw`.

*see https://freemyipod.org/wiki/Firmware for (incomplete) technical details!*

### unpack
unpacks an MSE file into a directory as a series of IMG1 files.
```py
from pathlib import Path
from ipodhax.mse import unpack_mse

input_path = Path("Firmware.MSE")
output_dir = Path("firmware")
output_dir.mkdir()

with open(input_path, "rb") as mse_stream:
  unpack_mse(mse_stream, output_dir)
```

### pack
packs a directory containing IMG1 files into an MSE file.
```py
from pathlib import Path
from ipodhax.mse import pack_mse

input_dir = Path("firmware")
output_path = Path("Firmware.MSE")

with open(output_path, "wb") as mse_stream:
  pack_mse(mse_stream, input_dir)
```

## IMG1
IMG1 is an image format used by non-iOS iPods based on the S5L CPU ([there are a lot of them](https://freemyipod.org/wiki/Hardware)) and some early iOS devices.  

newer [IMG2](https://www.theiphonewiki.com/wiki/S5L_File_Formats#IMG2) and [IMG3](https://www.theiphonewiki.com/wiki/IMG3_File_Format) formats were used in newer iOS devices, and the [IMG4](https://www.theiphonewiki.com/wiki/IMG4_File_Format) format lives on in iOS and Apple Watch devices to this day.
however non-iOS iPods (classic, nano, and shuffle) continued to use the IMG1 format, and starting with the 4th generation nano a newer 2.0 version of IMG1 is used, which this code implements.

*see https://freemyipod.org/wiki/IMG1 for technical details!*

### unpack
unpacks an IMG1 file into a directory containing `head.json`, `body.bin`, `cert.bin` and `sign.bin`.
```py
from pathlib import Path
from ipodhax.img1 import unpack_img1

input_path = Path("firmware") / "rsrc.img1"
output_dir = Path("rsrc")
output_dir.mkdir()

with open(input_path, "rb") as img1_stream:
  unpack_img1(img1_stream, output_dir)
```

### pack
packs an unpacked IMG1 directory into an IMG1 file.
```py
from pathlib import Path
from ipodhax.img1 import pack_img1

input_path = Path("rsrc")
output_path = Path("rsrc.img1")

with open(output_path, "wb") as img1_stream:
  pack_img1(img1_stream, output_path)
```
