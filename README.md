# OrcaSlicer X3G Writer for ZYYX+

Export a local `.x3g` file from OrcaSlicer for a single-extruder ZYYX+. This Python post-processing script prepares the slicer's G-code for GPX and tells Orca to save GPX's binary output with the correct extension.

**This is an AI-developed community project.** It is independent of OrcaSlicer, Cura, ZYYX and the authors of the tools it uses.

## Before installing

- Tested on **Linux with OrcaSlicer 2.5.1, Python 3 and GPX 2.6.8**. No Python packages are required.
- You need a GPX executable with the `z` (ZYYX single-extruder) machine definition. The Linux binary bundled with Cura 5.11's X3GWriter was used for verification.
- You need an **already compatible Orca printer setup**. This is not a general Marlin-to-X3G converter. The writer expects the ported ZYYX+ start and end sequences, absolute extrusion and an unheated bed. See `START`, `END` and `normalize()` in [the script](orca-zyyx-x3g.py) for the exact input contract. In the start sequence, the nozzle `M104` line is executable G-code; the other commands carry the `;ZYYX_X3G ` prefix so Orca preserves them for export. The writer rejects a mismatched sequence. No slicer profiles or GPX binaries are distributed here.

## Install on Linux

1. If you don't already have GPX with ZYYX support, install **X3GWriter** from Cura's Marketplace and restart Cura. For Cura 5.11 the writer looks for `~/.local/share/cura/5.11/plugins/X3GWriter/X3GWriter/gpx`. For another installation, locate the executable with:

   ```sh
   find "$HOME/.local/share/cura" -type f -name gpx
   ```

2. Download the writer and print its absolute path:

   ```sh
   git clone https://github.com/danieloldberg/orca-zyyx-x3g-writer.git
   cd orca-zyyx-x3g-writer
   realpath orca-zyyx-x3g.py
   ```

3. In OrcaSlicer, duplicate the ZYYX+ **process** preset. Under **Post-processing scripts**, enter the line below, replacing the example path with the one printed above. Use it as the only post-processor: its output is binary.

   ```text
   /usr/bin/python3 "/absolute/path/to/orca-zyyx-x3g.py"
   ```

   If GPX isn't at the default location, use this line instead:

   ```text
   /usr/bin/python3 "/absolute/path/to/orca-zyyx-x3g.py" --gpx "/absolute/path/to/gpx"
   ```

4. Save and select the new process preset. To uninstall, remove the post-processing line (or delete the duplicate preset), then remove the downloaded directory.

## Export and verify

Slice a small model, select **Export G-code file** and choose a fresh local filename such as `cube-01.gcode`. Look for **`cube-01.x3g`** in that directory. Orca's dialog and completion message may still say `.gcode`. An existing `.x3g` is not overwritten. Use local file export rather than **Print/Send** or `.gcode.3mf` export.

If the writer reports `M190` or `M140`, check the filament assigned to the model: all bed temperatures must be **0 °C** for this unheated printer. Orca 2.5.1 can report *“Filament 1 cannot be printed directly on the surface of this plate”* at 0 °C; this does not prevent local file export. Do not raise the bed temperature to suppress it.

**Verification scope:** Local GUI export and decoding were tested. On a PLA cube, the decoded homing, three-point probing, nozzle wait and priming sequence matched a CuraEngine reference. Physical printing has not been verified.

## Credits

The original Cura plugin [**X3GWriter**](https://github.com/Ghostkeeper/X3GWriter) was created by **[Ghostkeeper](https://github.com/Ghostkeeper)**. Its approach of passing slicer output to GPX, and its bundled ZYYX-capable converter, made this Orca integration possible. The actual X3G encoding is performed by **[GPX](https://github.com/Ghostkeeper/GPX)**, not by this Python script.
