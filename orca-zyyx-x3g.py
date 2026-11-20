#!/usr/bin/env python3
"""OrcaSlicer local export hook for the ZYYX+ profile."""

import argparse
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile


MARKER = ";ZYYX_X3G "
# Pin the executable parts of the ported profile, except the material temperature.
# A changed or incomplete start/end block must be reviewed, not silently printed.
START = """\
M73 P0
M104 S{temperature} T0
M126 S0
G21
G90
G130 X80 Y80 A127 B127
G162 X Y F2500
G92 X0 Y0
G1 X-5 Y-5 F2500
G162 X Y F200
G92 X132.5 Y120
G161 Z F1100
G92 Z0
G1 Z2 F1100
G161 Z F100
G92 Z0
M132 Z
M131 A
G1 Z2 F1100
G1 X-44.5 Y120 F7000
G161 Z F100
M131 B
G1 Z2 F1100
G1 X132.5 Y-110 F7000
G161 Z F100
M131 AB
G1 Z2 F1100
M132 AB
G1 Z1 F1000
M82
M133 T0
M126 S0
G4 P1000
G1 X80 Y-110 Z0.2 F1000
G1 X20 E9 F1000
G1 X-20 E12.5 F1000
G92 E0""".splitlines()
END = """\
M73 P100
G0 Z195 F1000
M104 S0 T0
M127
G162 X Y F3000
M18
M70 P5 (ZYYX Print Finished!)
M72 P1""".splitlines()
NUMBER = r"-?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
MOVE = re.compile(r"G[01](?: [XYZEF]" + NUMBER + r")+")
NOZZLE = re.compile(r"M104 S([0-9]+)(?: T0)?")
# In GPX's MakerBot mode M109 also controls the bed, not the nozzle.
BED_HEAT = re.compile(r"M0*(?:109|140|190)(?![0-9.])", re.IGNORECASE)
FAN = re.compile(r"M106(?: S([0-9]+))?(?: P0)?")
G92_WARNING = "warning G92 emulation unable to determine all coordinates to set via x3g:140 set extended position"


def find_gpx(override):
    def executable(path):
        return path.is_file() and os.access(path, os.X_OK)

    if override is not None:
        if not executable(override):
            raise ValueError(f"--gpx pekar inte på en körbar fil: {override}")
        return override.resolve(strict=True)

    for path in (
        Path(__file__).resolve().with_name("gpx"),
        Path.home() / ".local/libexec/orca-zyyx-x3g/gpx",
    ):
        if executable(path):
            return path.resolve(strict=True)
    on_path = shutil.which("gpx")
    if on_path:
        return Path(on_path).resolve(strict=True)
    raise ValueError("Hittar inte GPX. Kör ./install.sh eller ange --gpx /sökväg/till/gpx (med maskinläget z).")


def normalize(source, ready):
    lines = source.read_text(encoding="utf-8").splitlines()
    marked = [line.startswith(MARKER) for line in lines]
    commands = [
        " ".join((line[len(MARKER):] if marker else line).split(";", 1)[0].split())
        for line, marker in zip(lines, marked)
    ]
    active = [i for i, command in enumerate(commands) if command]
    # Orca can emit bed heating before the pinned start block.
    for i in active:
        if BED_HEAT.match(commands[i]):
            raise ValueError(
                f"Rad {i + 1}: {commands[i]} begär bäddvärme, men ZYYX+ har ingen uppvärmd bädd. "
                "Kontrollera vald platta i Orca och gå igenom filamentvalet för varje objekt. "
                "Välj matchande ZYYX+-filament med 0 °C bäddtemperatur för den valda plattan, "
                "skiva om och exportera igen."
            )
    if len(active) <= len(START) + len(END):
        raise ValueError("ZYYX+:s startblock, rörelser eller slutblock saknas")
    start, body, end = active[:len(START)], active[len(START):-len(END)], active[-len(END):]
    temp = NOZZLE.fullmatch(commands[start[1]])
    if not temp or not 0 < int(temp[1]) <= 280:
        raise ValueError("Förväntade en giltig M104-temperatur i startblocket")
    for i, expected in zip(start, START):
        is_temperature = "{temperature}" in expected
        if commands[i] != expected.format(temperature=temp[1]) or marked[i] == is_temperature:
            raise ValueError(f"Rad {i + 1}: oväntat startblock; välj ZYYX+ 0.4 mm (Cura)")
    if any(marked[i] for i in body + end) or [commands[i] for i in end] != END:
        raise ValueError("Oväntade ZYYX-markörer eller ändrat slutblock")
    if not any(MOVE.fullmatch(commands[i]) for i in body):
        raise ValueError("Ingen objektrörelse efter startblocket")

    for i in body:
        command = commands[i]
        nozzle = NOZZLE.fullmatch(command)
        fan = FAN.fullmatch(command)
        if fan and (fan[1] is None or 0 <= int(fan[1]) <= 255):
            # MakerBot M106 toggles the heatsink fan, not the ZYYX part blower.
            commands[i] = "M127" if fan[1] is not None and int(fan[1]) == 0 else "M126"
        elif command in ("M107", "M107 P0"):
            commands[i] = "M127"
        elif re.fullmatch(r"M204 S[0-9]+", command):
            # GPX 2.6.8 does not implement this Marlin acceleration command.
            commands[i] = ""
        elif not (
            MOVE.fullmatch(command)
            or command in ("G90", "G21", "M82", "G92 E0")
            or nozzle and 0 <= int(nozzle[1]) <= 280
        ):
            raise ValueError(f"Rad {i + 1}: kommandot stöds inte i prototypen: {command}")

    # Keep line numbers, but do not give GPX comments (including GPX macros).
    ready.write_text("\n".join(commands) + "\n", encoding="ascii")
    partial_xy = {
        "G92 X0 Y0": "X:0.00 Y:0.00",
        "G92 X132.5 Y120": "X:132.50 Y:120.00",
    }
    return {i + 1: partial_xy[commands[i]] for i in start if commands[i] in partial_xy}


def convert(source, gpx, output_name):
    if os.environ.get("SLIC3R_PP_HOST") != "File":
        raise ValueError("Endast lokal Orca-export (SLIC3R_PP_HOST=File) stöds")
    if source.suffix != ".pp" or not stat.S_ISREG(source.lstat().st_mode):
        raise ValueError("Förväntade en vanlig temporär .pp-fil från Orca, inte original-G-koden")
    if not output_name or "\r" in output_name or "\n" in output_name:
        raise ValueError("SLIC3R_PP_OUTPUT_NAME saknas eller är ogiltigt")
    dest = Path(output_name)
    if not dest.is_absolute() or dest.suffix.lower() not in (".gcode", ".x3g") or not dest.parent.is_dir():
        raise ValueError("Förväntade en absolut lokal .gcode- eller .x3g-sökväg från Orca")
    dest = dest.with_suffix(".x3g")
    if dest.exists() or dest.is_symlink():
        raise ValueError(f"Exporten skulle skriva över {dest}; välj ett nytt namn")
    sidecar = source.with_name(source.name + ".output_name")
    build_name = re.sub(r"[^a-zA-Z0-9 _-]", "_", dest.stem)[:23].strip() or "ZYYX"
    with tempfile.TemporaryDirectory(prefix=".zyyx-x3g-", dir=source.parent) as temp_dir:
        staging = Path(temp_dir)
        ready, converted = staging / (build_name + ".gcode"), staging / (build_name + ".x3g")
        allowed_g92 = normalize(source, ready)
        result = subprocess.run(
            [str(find_gpx(gpx)), "-I", "-g", "-p", "-m", "z", str(ready), str(converted)],
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env={**os.environ, "LC_ALL": "C"}, text=True, encoding="utf-8", errors="replace",
        )
        diagnostics = iter(result.stdout.splitlines())
        for line in diagnostics:
            warning = re.fullmatch(r"\(line ([0-9]+)\) " + re.escape(G92_WARNING), line)
            if not warning or int(warning[1]) not in allowed_g92:
                raise ValueError(f"Oväntad GPX-diagnostik:\n{result.stdout.strip()}")
            position = allowed_g92[int(warning[1])]
            if next(diagnostics, "") != f"current position defined as {position} Z:0.00 A:0.00 B:0.00":
                raise ValueError(f"Oväntad GPX-diagnostik:\n{result.stdout.strip()}")
        if result.returncode:
            raise ValueError(f"GPX misslyckades (kod {result.returncode})")
        if not converted.is_file() or converted.stat().st_size < 6:
            raise ValueError("GPX skapade ingen användbar X3G-fil")
        with converted.open("rb") as data:
            if data.read(1) != b"\x99":  # X3G host command 153, Start Build
                raise ValueError("GPX-resultatet saknar X3G:s byggstart")

        # Orca expects the input pathname to survive and reads the new basename
        # from the sidecar. Stage both on the same filesystem before publishing.
        name_file = staging / "output_name"
        name_file.write_text(dest.name + "\n", encoding="utf-8")
        os.link(name_file, sidecar)  # Don't follow or overwrite existing entries.
        try:
            os.replace(converted, source)
        except OSError:
            sidecar.unlink()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gpx", type=Path,
        help="sökväg till GPX-binären (annars bredvid skriptet, i användarens libexec eller på PATH)",
    )
    parser.add_argument("source", type=Path, help="Orcas temporära .pp-fil, bifogas av Orca")
    args = parser.parse_args()
    try:
        convert(args.source.absolute(), args.gpx, os.environ.get("SLIC3R_PP_OUTPUT_NAME"))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ZYYX X3G: {exc}\n")


if __name__ == "__main__":
    main()
