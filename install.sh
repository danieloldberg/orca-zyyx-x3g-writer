#!/bin/sh
set -eu

# markwal/GPX tag 2.6.8. Pin the commit and the SHA-256 of its codeload tarball.
version=2.6.8
commit=28f346005ee37117b1f042dd66570d108726a02f
sha256=d9d269a7b4c7804377e7fa41e5a467b93c7943c9b56a9a047e77938962ab7aef
url="https://codeload.github.com/markwal/GPX/tar.gz/$commit"

if [ "$(uname -s)" != Linux ]; then
    echo 'This installer supports Linux only.' >&2
    exit 1
fi
if [ "$#" -ne 0 ]; then
    echo "Usage: $0" >&2
    exit 1
fi
case ${HOME:-} in
    /*) ;;
    *) echo 'HOME must be an absolute path.' >&2; exit 1 ;;
esac
for tool in cc make curl tar gzip sha256sum install python3; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "Required tool not found: $tool" >&2
        exit 1
    fi
done

export LC_ALL=C
repo=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
target="$HOME/.local/libexec/orca-zyyx-x3g"
orca_line=$(python3 -c 'import shlex, sys; print(shlex.quote(sys.executable), shlex.quote(sys.argv[1]))' \
    "$target/orca-zyyx-x3g.py")
work=$(mktemp -d "${TMPDIR:-/tmp}/orca-zyyx-gpx.XXXXXXXX")
stage=
cleanup() {
    if [ -n "$stage" ]; then
        rm -rf -- "$stage"
    fi
    rm -rf -- "$work"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

echo "Downloading and building GPX $version from verified upstream source..." >&2
(
    cd -- "$work"
    curl --disable --fail --silent --show-error --location --proto '=https' --proto-redir '=https' \
        --output gpx.tar.gz "$url"
    printf '%s  %s\n' "$sha256" gpx.tar.gz | sha256sum --check --strict
    tar -xzf gpx.tar.gz
    cd "GPX-$commit"
    # The release includes generated Autotools files. Build only the CLI, using
    # a pre-C23 dialect for this release and no path-dependent debug symbols.
    CONFIG_SITE=/dev/null ./configure --disable-dependency-tracking CC=cc CFLAGS='-O2 -std=gnu11'
    make -C src/gpx gpx
    src/gpx/gpx -I '-?' > gpx-help.txt 2>&1
    if ! grep -Fxq "GPX $version" gpx-help.txt ||
        ! grep -Eq '^[[:space:]]+z[[:space:]]+=[[:space:]]+ZYYX - single extruder$' gpx-help.txt; then
        echo "The built GPX does not identify as $version with ZYYX machine mode z." >&2
        exit 1
    fi
) >&2

install -d -m 700 -- "$target"
stage=$(mktemp -d "$target/.install.XXXXXXXX")
install -m 755 -- "$work/GPX-$commit/src/gpx/gpx" "$stage/gpx"
install -m 755 -- "$repo/orca-zyyx-x3g.py" "$stage/orca-zyyx-x3g.py"
mv -fT -- "$stage/gpx" "$target/gpx"
mv -fT -- "$stage/orca-zyyx-x3g.py" "$target/orca-zyyx-x3g.py"

printf 'Installed GPX %s and the writer in %s\n' "$version" "$target" >&2
printf 'Paste this line into OrcaSlicer Post-processing scripts:\n' >&2
printf '%s\n' "$orca_line"
