# OrcaSlicer X3G Writer for ZYYX+

Export a local `.x3g` file from OrcaSlicer for a single-extruder ZYYX+. The writer uses GPX to encode Orca's G-code.

**This is an independent, AI-developed community project.**

## Before installing

- Tested on **Linux with OrcaSlicer 2.5.1, Python 3 and GPX 2.6.8**. No Python packages are required.
- The installer checks the SHA-256 of the pinned upstream [GPX 2.6.8 source](https://github.com/markwal/GPX/releases/tag/2.6.8) and builds a private copy with the `z` (ZYYX single-extruder) machine definition. It does not install a slicer or modify your Orca profiles.
- You need an **already compatible Orca printer setup**. This is not a general Marlin-to-X3G converter. The writer expects the ported ZYYX+ start and end sequences, absolute extrusion and an unheated bed. See `START`, `END` and `normalize()` in [the script](orca-zyyx-x3g.py) for the exact input contract. In the start sequence, the nozzle `M104` line is executable G-code; the other commands carry the `;ZYYX_X3G ` prefix so Orca preserves them for export. The writer rejects a mismatched sequence. No slicer profiles or GPX binaries are distributed here.

## Install on Linux

You need Git, Python 3, `curl` with HTTPS support, GNU coreutils and tar, `gzip`, and a C compiler (`cc`) with libc development headers and GNU Make. On Debian/Ubuntu the main build dependencies are `build-essential` and `curl`. Autoconf and Automake are not required; the upstream source includes the generated build files.

1. Clone this repository and run the installer as your normal user:

   ```sh
   git clone https://github.com/danieloldberg/orca-zyyx-x3g-writer.git
   cd orca-zyyx-x3g-writer
   ./install.sh
   ```

2. The installer puts `orca-zyyx-x3g.py` and `gpx` in `~/.local/libexec/orca-zyyx-x3g/`. In OrcaSlicer, duplicate your ZYYX+ **process** preset, or edit the copy you already use for X3G. In **Post-processing scripts**, paste the command printed by the installer. Use it as the only post-processor: its output is binary. For a typical Linux home it looks like this:

   ```text
   /usr/bin/python3 "/home/YOUR_USER/.local/libexec/orca-zyyx-x3g/orca-zyyx-x3g.py"
   ```

   **Already have a compatible standalone GPX?** Skip the installer, keep the cloned repository, and enter both absolute paths instead:

   ```text
    /usr/bin/python3 "/absolute/path/to/orca-zyyx-x3g.py" --gpx "/absolute/path/to/gpx"
    ```

   Without `--gpx` the writer checks next to the script, then the install directory above, then `PATH`. The binary must support machine mode `z`.

3. Save and select the process preset. To upgrade an installed copy, run `git pull --ff-only` followed by `./install.sh`. To uninstall, remove the post-processing line from Orca and delete `~/.local/libexec/orca-zyyx-x3g/`.

## Export and verify

Slice a small model, select **Export G-code file** and choose a fresh local filename such as `cube-01.gcode`. Look for **`cube-01.x3g`** in that directory. Orca's dialog and completion message may still say `.gcode`. An existing `.x3g` is not overwritten. Use local file export rather than **Print/Send** or `.gcode.3mf` export.

If the writer reports `M190` or `M140`, check the filament assigned to the model: all bed temperatures must be **0 °C** for this unheated printer. Orca 2.5.1 can report *“Filament 1 cannot be printed directly on the surface of this plate”* at 0 °C; this does not prevent local file export. Do not raise the bed temperature to suppress it.

**Verification scope:** A PLA cube was exported through OrcaSlicer's GUI and decoded successfully. The standalone GPX build reproduced the same X3G file byte for byte from the same G-code. Physical printing has not been verified.

## Credits

Thanks to [Ghostkeeper](https://github.com/Ghostkeeper), author of the original [X3GWriter](https://github.com/Ghostkeeper/X3GWriter).
