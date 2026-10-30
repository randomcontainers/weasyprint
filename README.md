# weasyprint

Container images with [WeasyPrint](https://weasyprint.org/), the command-line tool that turns HTML and CSS into PDF documents laid out for print. `latest` also includes qpdf, which encrypts, linearizes, splits and merges the PDFs that WeasyPrint writes. The images are rebuilt when WeasyPrint publishes a release and when the base image changes, for `linux/amd64` and `linux/arm64`.

This is an unofficial build, not affiliated with or endorsed by the WeasyPrint project. Report problems with the image in this repository and problems with WeasyPrint itself [upstream](https://github.com/Kozea/WeasyPrint/issues).

## Quick start

Convert an HTML file in the current directory:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" \
  ghcr.io/randomcontainers/weasyprint report.html report.pdf
```

Images, stylesheets and fonts that the HTML links with relative URLs are read from the directory of the HTML file, so keep them inside the mounted directory. Add a stylesheet with `--stylesheet`, and choose a PDF/A, PDF/UA or PDF/X variant with `--pdf-variant`:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" \
  ghcr.io/randomcontainers/weasyprint --stylesheet print.css --pdf-variant pdf/a-3b report.html report.pdf
```

Without arguments the image prints `weasyprint --help`, which lists every option and variant.

With `-` in place of the file names, WeasyPrint reads the HTML from standard input and writes the PDF to standard output. Relative URLs are then resolved against `/work`:

```sh
docker run --rm -i ghcr.io/randomcontainers/weasyprint - - < report.html > report.pdf
```

The default image also has qpdf. Run it by replacing the entrypoint, for example to protect a PDF with a password:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" --entrypoint qpdf \
  ghcr.io/randomcontainers/weasyprint \
  --encrypt --user-password=secret --owner-password=owner --bits=256 -- report.pdf report-locked.pdf
```

## What is in the image

| | slim | default |
|---|---|---|
| WeasyPrint and its Python dependencies, installed from `requirements.lock` | yes | yes |
| Pango, HarfBuzz and Fontconfig from the distro, which WeasyPrint uses to lay out text | yes | yes |
| The DejaVu fonts | yes | yes |
| qpdf, to encrypt, linearize, split, merge and repair PDFs | no | yes |

qpdf is the [randomcontainers/qpdf](https://github.com/randomcontainers/qpdf) build. EPS images are not rendered, because WeasyPrint turns off Pillow's use of Ghostscript.

The lock leaves out zopfli, which fontTools uses only to write compressed WOFF files. WeasyPrint reads WOFF and WOFF2 fonts but never writes them.

### Fonts

The images have the DejaVu fonts only. On Ubuntu, `fonts-dejavu-core` and `fonts-dejavu-mono` have the regular and bold styles of DejaVu Sans and DejaVu Serif and every style of DejaVu Sans Mono, and `fonts-dejavu-extra` adds the italic, condensed and extra-light styles to an image built on `slim`. On Alpine, `font-dejavu` has all of them. `serif`, `sans-serif` and `monospace` map to DejaVu Serif, DejaVu Sans and DejaVu Sans Mono. Text in a script that DejaVu does not cover, such as Chinese, Japanese or Korean, needs another font. Load one with `@font-face` from a file next to the HTML (TrueType, OpenType, WOFF and WOFF2 work), or install font packages in an image built on `slim`.

Color fonts with COLR glyphs, which some emoji fonts use, are drawn in color on Alpine only. WeasyPrint draws them with HarfBuzz's `libharfbuzz-vector`, which the HarfBuzz 13 in Alpine 3.24 has and the HarfBuzz 12 in Ubuntu 26.04 does not. On Ubuntu, WeasyPrint prints a warning for such fonts.

## Default or slim

The default image (`latest`) has WeasyPrint and qpdf and is recommended for general use. qpdf does what WeasyPrint does not: password protection, linearization for fast web view, and splitting, merging and repairing PDFs. Use `slim`, which has WeasyPrint only, as the base when you build your own image and want that base kept up to date.

The default image is also published as `ghcr.io/randomcontainers/weasyprint-qpdf`, built in the [weasyprint-qpdf](https://github.com/randomcontainers/weasyprint-qpdf) repository with the same contents and a different digest.

## Tags

`<version>` is a WeasyPrint release such as `70.0`. `<major>` is its shorter form, `70`, and follows the newest release in that series.

| Default (with qpdf) | Slim | Base |
|---|---|---|
| `latest`, `<version>`, `<major>` | `slim`, `<version>-slim`, `<major>-slim` | Ubuntu |
| `ubuntu`, `<version>-ubuntu`, `<major>-ubuntu` | `slim-ubuntu`, `<version>-slim-ubuntu`, `<major>-slim-ubuntu` | Ubuntu |
| `<version>-ubuntu26.04` | `<version>-slim-ubuntu26.04` | Ubuntu 26.04 |
| `alpine`, `<version>-alpine`, `<major>-alpine` | `slim-alpine`, `<version>-slim-alpine`, `<major>-slim-alpine` | Alpine |
| `<version>-alpine3.24` | `<version>-slim-alpine3.24` | Alpine 3.24 |

The images are currently built on Ubuntu 26.04 and Alpine 3.24. Tags without a distro version move to the next distro release when the project does; tags ending in `ubuntu26.04` or `alpine3.24` stay on that release and are no longer rebuilt once the project moves to the next one. Every tag of the current WeasyPrint version, including the exact version, is rebuilt in place (see [Updates](#updates)), so pin a digest when you need the same bytes every time.

## Platforms

`linux/amd64` and `linux/arm64`, for both Ubuntu and Alpine. Both are built natively on GitHub-hosted runners, without emulation. WeasyPrint's Python dependencies are installed from prebuilt wheels: manylinux wheels on Ubuntu and musllinux wheels on Alpine.

## Files and permissions

The working directory is `/work`. The image runs as UID 1000, and any other UID works too: `HOME` is then `/`, and caches go to `/cache`, which anyone can write to. How to get output files owned by you depends on how you run containers:

| Runtime | Flag |
|---|---|
| Docker on Linux (rootful), GitHub Actions | `--user "$(id -u):$(id -g)"` |
| Rootless Podman | `--userns=keep-id` |
| Rootless Docker | `--user 0:0` (root in the container is your user on the host) |
| Docker Desktop on macOS or Windows | none, file ownership is mapped for you |

## Untrusted HTML

WeasyPrint loads every resource a document refers to, over the network or from local files, and a document can ask for files to be attached to the PDF. HTML that someone else wrote can use this to reach services on your network or to copy files it can read into the PDF. Run it without a network and with `--allowed-protocols data`, which lets WeasyPrint load `data:` URLs, such as inline images and fonts, and nothing else:

```sh
docker run --rm -i --network none ghcr.io/randomcontainers/weasyprint \
  --allowed-protocols data - - < untrusted.html > untrusted.pdf
```

Without `--allowed-protocols`, WeasyPrint also opens `file:` URLs, so even without a network or a mounted directory the document could copy files from the container into the PDF, such as `/proc/self/environ` with the variables passed with `-e`. The HTML on standard input and the files named on the command line, such as a `--stylesheet`, are read directly and are not affected by the option.

When the document needs resources from the web, use `--allowed-protocols https,data`. With `https` alone, `data:` URLs are refused too. An `https` URL can still point at a host on your network, so restrict the container's network as well. WeasyPrint releases have fixed server-side request forgery bugs, for example CVE-2025-68616 in 68.0 and CVE-2026-55073 in 70.0, and the images usually pick up a new release about a day after it is published (see [Updates](#updates)).

## Extending the slim image

Use a `slim` tag as the base for your own image. `slim`, `slim-ubuntu` and `slim-alpine` follow new WeasyPrint releases and are rebuilt when its locked Python dependencies or the distro change. WeasyPrint runs from a virtual environment in `/usr/local/lib/weasyprint`; the `python3` on `PATH` is the distro's interpreter and cannot import WeasyPrint, so run Python code that uses WeasyPrint as a library with `/usr/local/lib/weasyprint/bin/python`. The distro packages WeasyPrint needs are listed in `/usr/local/share/randomcontainers/weasyprint/runtime-deps`. Switch to root to install more, for example the Liberation fonts, which have the metrics of Arial, Times New Roman and Courier New, then back:

```dockerfile
FROM ghcr.io/randomcontainers/weasyprint:slim-ubuntu@sha256:...
USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends fonts-liberation \
 && rm -rf /var/lib/apt/lists/*
USER 1000:1000
```

On Alpine, use `apk add --no-cache font-liberation`. The entrypoint is `["tini", "--", "weasyprint"]`; set your own `ENTRYPOINT` if your image runs a script. To pick up new WeasyPrint releases and base image fixes, let Dependabot or Renovate update the digest in your `FROM` line.

## Verifying

Each image has a build provenance attestation from this repository's GitHub Actions run, signed by the shared build workflow in `randomcontainers/ci`:

```sh
gh attestation verify oci://ghcr.io/randomcontainers/weasyprint:latest \
  --repo randomcontainers/weasyprint --signer-repo randomcontainers/ci
```

Images from `ghcr.io/randomcontainers/weasyprint-qpdf` are built in that repository, so verify them with `--repo randomcontainers/weasyprint-qpdf` and the same `--signer-repo`.

Each platform image also carries an SPDX SBOM that lists the distro and Python packages in it with their versions:

```sh
docker buildx imagetools inspect ghcr.io/randomcontainers/weasyprint:latest --format '{{ json .SBOM }}'
```

WeasyPrint and all of its Python dependencies are installed from [`requirements.lock`](requirements.lock), which pins every package to a version and its SHA-256 hashes, and pip refuses anything else. The URL and hash of each installed wheel are in `/usr/local/share/randomcontainers/weasyprint/source`.

## Updates

The project checks [weasyprint on PyPI](https://pypi.org/project/weasyprint/) every 15 minutes. A release is picked up once it is 24 hours old and PyPI holds a provenance attestation showing it was published from the [Kozea/WeasyPrint](https://github.com/Kozea/WeasyPrint) repository. The new version and a regenerated `requirements.lock` are then committed together and the images are rebuilt. Only the newest release is built; tags of older versions stay as they were last built. Dependency versions in the lock must have been on PyPI for at least a day. The lock is also regenerated weekly at the same WeasyPrint version, so fixes in dependencies such as fontTools and tinycss2 reach the current tags between releases. The license files in [`licenses/`](licenses/) belong to one version of Pillow and one of Pyphen. When a new lock moves either of them to another version, the whole update waits, a new WeasyPrint release included, until those files are refreshed and committed by hand together with the lock (see [Building](#building)).

The images of the current version are also rebuilt when the Ubuntu or Alpine base image changes, the default ones when a new qpdf image is published, and all of them at least every 7 days, so distro security fixes reach the current tags.

## Building

```sh
docker build -f Dockerfile.ubuntu --target slim --build-arg VERSION=<version> -t weasyprint:local .
```

Use `Dockerfile.alpine` for the Alpine image. `<version>` must be the version pinned in `requirements.lock`; the build stops otherwise. The default image is generated from the `combos` section of `package.yml` by [randomcontainers/ci](https://github.com/randomcontainers/ci) and layers qpdf onto this image. The command that produced `requirements.lock` is at the top of the file; it resolves for Python 3.14, the version on both bases, and leaves out zopfli. If a new lock changes the Pillow version, run `python3 scripts/bundled-licenses.py` to refresh `licenses/pillow-<version>/`. If it changes the Pyphen version, check the licenses of the hyphenation dictionaries in the new release against `licenses/pyphen-<version>/dictionaries/README`, update that file and the `license` in `package.yml` if they changed, and rename the directory to the new version. The build fails until the directories in `licenses/` match the installed Pillow and Pyphen.

## Licenses

WeasyPrint is released under the [BSD 3-Clause license](https://github.com/Kozea/WeasyPrint/blob/main/LICENSE). The slim image adds its Python dependencies, which are mostly under BSD and MIT licenses, with Pillow under MIT-CMU and parts of fontTools under Apache-2.0, plus pip (MIT), which includes packages under the Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC, MIT, MPL-2.0 and PSF-2.0 licenses. Each package's license files are in `/usr/local/share/randomcontainers/weasyprint/licenses/`.

Pyphen, which WeasyPrint uses for hyphenation, is available under GPL-2.0-or-later, LGPL-2.1-or-later or MPL-1.1 and is used here under LGPL-2.1-or-later. Its hyphenation dictionaries come from LibreOffice and are in the `pyphen/dictionaries/` directory of the virtual environment. Each has its own license, stated in a `README_hyph_*.txt` file or at the top of the `.dic` file; a few carry no license statement. The dictionaries for Czech, Galician, Kannada, Norwegian (Bokmål and Nynorsk), European Portuguese, Romanian and Ukrainian are under the GNU GPL only. Pyphen's license files include version 2 of the GPL, and this repository adds version 3, which the Galician and Kannada dictionaries refer to, in [`licenses/`](licenses/). The images have it, with a list of the GPL dictionaries, in `/usr/local/share/randomcontainers/weasyprint/licenses/pyphen/dictionaries/`.

Pillow's Linux wheels include about twenty libraries that its extension modules use, such as FreeType, libjpeg-turbo, libpng, libtiff and libwebp, and Pillow's LICENSE file, in `/usr/local/share/randomcontainers/weasyprint/licenses/pillow/` in the image, has the license of each. The musllinux wheels used on Alpine also include libbsd and libmd, whose licenses are not in the wheel, so this repository adds their license files in [`licenses/`](licenses/), and the images have them in `/usr/local/share/randomcontainers/weasyprint/licenses/pillow/bundled/`. The `SOURCES` file there names the Pillow wheels and the source archive of each library with its SHA-256.

The SPDX expression in the image's `org.opencontainers.image.licenses` label has to fit in 256 characters. It includes GPL-2.0-or-later and GPL-3.0-only for the GPL dictionaries. It leaves out MIT-0 (cffi) and 0BSD (liblzma), which set no conditions, Beerware, which covers a few files of libbsd and libmd, the MIT-style X11, MIT-open-group and TCL licenses of some of the code in Pillow's wheels, and the licenses of the other hyphenation dictionaries.

`latest` also contains qpdf, licensed under the Apache License 2.0. Its license files are described in the [qpdf repository](https://github.com/randomcontainers/qpdf#licenses).

The files in this repository are available under the MIT license, see [LICENSE](LICENSE), except the license texts in `licenses/`, which keep their own terms.

## Requesting a tool

To suggest another tool, use the [Request a tool](https://github.com/randomcontainers/.github/issues/new?template=tool-request.yml) form.
