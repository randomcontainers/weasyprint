"""Collect the license files of libraries in Pillow's wheels that its LICENSE leaves out.

Usage: bundled-licenses.py

Pillow's Linux wheels include the shared libraries its extension modules
use, and the wheel's LICENSE file has the license of every library Pillow
builds for them. The musllinux wheels, which the Alpine image installs, also
include libbsd and libmd, which libXdmcp needs. They come from the Alpine
system the wheels are built on, and no file in the wheel has their licenses.

This reads the Pillow version from requirements.lock, downloads the
musllinux wheels the lock pins for x86_64 and aarch64, checks them against
their SHA-256, and lists the libraries in pillow.libs/. It stops when a
library is neither covered by a section of the wheel's LICENSE nor listed in
EXTERNAL below. For the listed ones it downloads the source release that
matches the library's version and writes its license files and the URL and
SHA-256 of the archive to licenses/pillow-<version>/bundled/. Run it
whenever the Pillow pin in requirements.lock changes.
"""

import hashlib
import io
import json
import pathlib
import re
import shutil
import sys
import tarfile
import textwrap
import urllib.request
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCHES = ("x86_64", "aarch64")

# Library in pillow.libs/: the section of Pillow's LICENSE that covers it.
COVERED = {
    "libXau": "XAU",
    "libXdmcp": "XDMCP",
    "libavif": "LIBAVIF",
    "libbrotlicommon": "BROTLI",
    "libbrotlidec": "BROTLI",
    "libfreetype": "FREETYPE2",
    "libharfbuzz": "HARFBUZZ",
    "libjpeg": "LIBJPEG",
    "liblcms2": "LCMS2",
    "liblzma": "LIBLZMA",
    "libopenjp2": "OPENJPEG",
    "libpng16": "LIBPNG",
    "libsharpyuv": "LIBWEBP",
    "libtiff": "LIBTIFF",
    "libwebp": "LIBWEBP",
    "libwebpdemux": "LIBWEBP",
    "libwebpmux": "LIBWEBP",
    "libxcb": "XCB",
    "libzstd": "ZSTD",
}

# Library in pillow.libs/: (release for each shared library version, source
# archive, license files). The shared library versions are the ones Alpine's
# package index lists for each release.
EXTERNAL = {
    "libbsd": (
        {"0.12.2": "0.12.2"},
        "https://libbsd.freedesktop.org/releases/libbsd-{version}.tar.xz",
        ["COPYING"],
    ),
    "libmd": (
        {"0.1.0": "1.1.0", "0.2.0": "1.2.0"},
        "https://libbsd.freedesktop.org/releases/libmd-{version}.tar.xz",
        ["COPYING"],
    ),
}

LIBRARY = re.compile(r"^pillow\.libs/(?P<name>.+?)-[0-9a-f]{8}\.so(?:\.(?P<version>[0-9.]+))?$")


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def locked(lock, name):
    match = re.search(rf"^{name}==([^\s;]+)((?:\s*\\\n\s*--hash=sha256:[0-9a-f]{{64}})+)", lock, re.M)
    if not match:
        sys.exit(f"requirements.lock does not pin {name}")
    return match.group(1), set(re.findall(r"sha256:([0-9a-f]{64})", match.group(2)))


def sections(text):
    return set(re.findall(r"^-{4}\n\n([A-Z0-9_]+)\n", text, re.M))


def main():
    lock = (ROOT / "requirements.lock").read_text()
    pillow, hashes = locked(lock, "pillow")
    match = re.search(r"--python-version 3\.(\d+)", lock)
    if not match:
        sys.exit("requirements.lock does not name the Python version it resolves for")
    python = f"cp3{match.group(1)}"

    release = json.loads(fetch(f"https://pypi.org/pypi/pillow/{pillow}/json"))
    wheels = {}
    for arch in ARCHES:
        suffix = f"-{python}-{python}-musllinux_1_2_{arch}.whl"
        found = [f for f in release["urls"] if f["filename"].endswith(suffix)]
        if len(found) != 1:
            sys.exit(f"pillow {pillow} has {len(found)} wheels named *{suffix} on PyPI")
        wheel = found[0]
        if wheel["digests"]["sha256"] not in hashes:
            sys.exit(f"requirements.lock does not list the hash of {wheel['filename']}")
        data = fetch(wheel["url"])
        if hashlib.sha256(data).hexdigest() != wheel["digests"]["sha256"]:
            sys.exit(f"{wheel['url']} does not match its SHA-256 on PyPI")
        wheels[arch] = (wheel, zipfile.ZipFile(io.BytesIO(data)))

    needed = {}
    for arch, (wheel, archive) in wheels.items():
        license_text = archive.read(f"pillow-{pillow}.dist-info/licenses/LICENSE").decode()
        covered = sections(license_text)
        libraries = {}
        for path in archive.namelist():
            match = LIBRARY.match(path)
            if match:
                libraries[match.group("name")] = match.group("version") or ""
        unknown = sorted(set(libraries) - set(COVERED) - set(EXTERNAL))
        if unknown:
            sys.exit(f"{wheel['filename']} includes libraries this script does not know: {unknown}")
        uncovered = sorted(n for n in libraries if n in COVERED and COVERED[n] not in covered)
        if uncovered:
            sys.exit(f"{wheel['filename']}: LICENSE has no section for {uncovered}")
        for name in sorted(set(libraries) & set(EXTERNAL)):
            versions, _, _ = EXTERNAL[name]
            if libraries[name] not in versions:
                sys.exit(f"{wheel['filename']}: add the release of {name}.so.{libraries[name]} to EXTERNAL")
            needed.setdefault(name, set()).add(versions[libraries[name]])
    for name, found in needed.items():
        if len(found) != 1:
            sys.exit(f"pillow {pillow} wheels include different releases of {name}: {sorted(found)}")

    intro = (
        f"Pillow {pillow}'s musllinux wheels, which the Alpine image installs, include "
        "libbsd and libmd from the Alpine system they are built on, because libXdmcp "
        "needs them. Pillow's LICENSE file covers the other libraries in the wheels but "
        "not these. The license files of each are in the directory of the same name, and "
        "the source release of the version in the wheels is listed below."
    )
    sources = [textwrap.fill(intro, 76, break_on_hyphens=False), "", f"pillow {pillow}"]
    for wheel, _ in wheels.values():
        sources += [f"  {wheel['url']}", f"  sha256:{wheel['digests']['sha256']}"]
    texts = {}
    for name in sorted(needed):
        (version,) = needed[name]
        _, template, files = EXTERNAL[name]
        url = template.format(version=version)
        data = fetch(url)
        with tarfile.open(fileobj=io.BytesIO(data)) as tar:
            top = f"{name}-{version}"
            try:
                texts[name] = {file: tar.extractfile(f"{top}/{file}").read() for file in files}
            except KeyError as missing:
                sys.exit(f"{url} has no {missing}")
        sources += [f"{name} {version}", f"  {url}", f"  sha256:{hashlib.sha256(data).hexdigest()}"]

    base = ROOT / "licenses"
    for old in base.glob("pillow-*"):
        shutil.rmtree(old)
    if not texts:
        print(f"pillow {pillow} includes no libraries outside its LICENSE")
        return
    out = base / f"pillow-{pillow}" / "bundled"
    for name, files in texts.items():
        (out / name).mkdir(parents=True)
        for file, content in files.items():
            (out / name / file).write_bytes(content)
    (out / "SOURCES").write_text("\n".join(sources) + "\n")
    print(f"wrote {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
