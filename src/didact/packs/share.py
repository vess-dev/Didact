"""Sharing packs: `.didactpack` files (a zip with a SHA-256 list), installing, and trust.

A `.didactpack` holds the pack's files plus `didactpack.json`: format, id, version, the
Didact version that made it, and the SHA-256 of every file. Installing checks every hash.
"""

import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import cast

from didact import __version__
from didact.core.clock import now_iso
from didact.core.errors import ConflictError, InvalidError
from didact.core.i18n import _
from didact.core.output import JSON
from didact.packs.build import build, file_hashes
from didact.packs.library import TRUST_FILE, Pack, PackLibrary, bundled_dir, version_key
from didact.store.fsutil import atomic_write

PACK_FORMAT = 1
INDEX = "didactpack.json"
SUFFIX = ".didactpack"
CATALOG = "index.json"  # beside the shipped packs: what's there, for updates
UPDATES = "https://raw.githubusercontent.com/vess-dev/Didact/main/packs/"
UPDATES_ENV = "DIDACT_PACK_UPDATES"  # another place to look for updates; empty: don't look


@dataclass(frozen=True, slots=True)
class Exported:
    path: Path
    files: int
    notes: list[str]


def export(root: Path, target: Path | None) -> Exported:
    """Validate a pack folder and write `<id>-<version>.didactpack`."""
    result = build(root)
    if result.bundle is None:
        message = (
            _("can't export: {problem}", problem=result.errors[0].text())
            if result.errors
            else _("can't export: it doesn't build")
        )
        raise InvalidError(message, hint=_("run `didact pack validate {path}`", path=root))
    manifest = cast(dict[str, JSON], result.bundle["manifest"])
    license_ = cast(dict[str, JSON], manifest.get("license") or {})
    pack_id, version = str(manifest["id"]), str(manifest["version"])
    if license_.get("redistributable") is False:
        raise InvalidError(
            _("{pack} is personal use only: its license doesn't allow sharing", pack=pack_id),
            hint=_("packs marked `redistributable: false` stay in your library"),
        )
    notes: list[str] = []
    hashes = file_hashes(root)
    extra: dict[str, bytes] = {}
    attribution = str(license_.get("attribution") or "")
    if attribution and not any(p.upper().startswith(("LICENSE", "ATTRIBUTION")) for p in hashes):
        spdx = license_.get("spdx") or "see the source"
        text = f"# Attribution\n\n{attribution}\n\nLicense: {spdx}\n"
        extra["ATTRIBUTION.md"] = text.encode()
        notes.append(_("added ATTRIBUTION.md from the manifest"))
    if manifest.get("plugins"):
        notes.append(_("it has Python plugins: whoever installs it must `didact pack trust` them"))
    index: dict[str, JSON] = {
        "format": PACK_FORMAT,
        "id": pack_id,
        "version": version,
        "didact": __version__,
        "exported": now_iso(),
        "files": {
            **hashes,
            **{name: hashlib.sha256(data).hexdigest() for name, data in extra.items()},
        },
    }
    out = target or Path.cwd()
    if out.is_dir() or not out.suffix:
        out = out / f"{pack_id}-{version}{SUFFIX}"
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(INDEX, json.dumps(index, indent=1, ensure_ascii=False))
        for rel in hashes:
            archive.write(root / rel, rel)
        for name, data in extra.items():
            archive.writestr(name, data)
    return Exported(out, len(hashes) + len(extra), notes)


@dataclass(frozen=True, slots=True)
class Installed:
    id: str
    version: str
    path: Path
    notes: list[str]


@dataclass(frozen=True, slots=True)
class Shipped:
    """A `.didactpack` that ships with Didact, ready to install."""

    id: str
    version: str
    kind: str
    name: str
    path: Path
    description: str = ""


def head_of(manifest: str) -> dict[str, str]:
    """A manifest's `kind`, `name` and `description`, read without a YAML parser (listing every
    pack stays quick): a value on its line, or a folded or literal block below it."""
    found: dict[str, str] = {}
    lines = manifest.splitlines()
    for index, line in enumerate(lines):
        key, colon, value = line.partition(":")
        if not colon or key not in ("kind", "name", "description") or key in found:
            continue
        value = value.strip()
        if value[:1] in (">", "|"):  # a block: the indented lines below it
            block: list[str] = []
            for more in lines[index + 1 :]:
                if more.strip() and not more[:1].isspace():
                    break
                block.append(more.strip())
            value = " ".join(part for part in block if part)
        elif len(value) > 1 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        if value:
            found[key] = value
    return found


def shipped(folder: Path | None = None) -> list[Shipped]:
    """The packs that ship with Didact as `.didactpack` files (or those in `folder`), by id."""
    folder = folder or bundled_dir()
    found: list[Shipped] = []
    for path in sorted(folder.glob(f"*{SUFFIX}")) if folder is not None else []:
        try:
            with zipfile.ZipFile(path) as archive:
                index = json.loads(archive.read(INDEX))
                manifest = archive.read("pack.yaml").decode("utf-8")
        except OSError, KeyError, ValueError, zipfile.BadZipFile:
            continue  # not a pack file: it isn't offered
        head = head_of(manifest)
        pack_id, version = str(index.get("id") or ""), str(index.get("version") or "")
        if pack_id and version:
            found.append(
                Shipped(
                    pack_id,
                    version,
                    head.get("kind", ""),
                    head.get("name", pack_id),
                    path,
                    head.get("description", ""),
                )
            )
    return sorted(found, key=lambda s: s.id)


def write_catalog(folder: Path) -> Path:
    """`index.json` for the `.didactpack` files in `folder`: where updates are looked up."""
    packs: list[JSON] = [
        {
            "id": p.id,
            "version": p.version,
            "kind": p.kind,
            "name": p.name,
            "file": p.path.name,
            "sha256": hashlib.sha256(p.path.read_bytes()).hexdigest(),
        }
        for p in shipped(folder)
    ]
    path = folder / CATALOG
    path.write_text(json.dumps({"format": PACK_FORMAT, "packs": packs}, indent=1) + "\n")
    return path


@dataclass(frozen=True, slots=True)
class Offer:
    """A newer version of an installed pack, and where it is."""

    id: str
    installed: str
    version: str
    source: str  # a local file or a URL
    sha256: str  # "" for a local file
    where: str


def updates(lib: PackLibrary) -> tuple[list[Offer], list[str]]:
    """Newer versions of the installed packs: in Didact's `packs/` folder, and on GitHub (or
    `$DIDACT_PACK_UPDATES`). Also notes on anything that couldn't be checked."""
    installed: dict[str, str] = {}
    for pack_id, refs in lib.available().items():
        mine = [r.version for r in refs if r.origin == "installed"]
        if mine:
            installed[pack_id] = max(mine, key=version_key)
    candidates = [Offer(s.id, "", s.version, str(s.path), "", "shipped folder") for s in shipped()]
    notes: list[str] = []
    base = os.environ.get(UPDATES_ENV, UPDATES)
    if base and installed:
        try:
            candidates += _remote(base)
        except (OSError, ValueError) as err:
            notes.append(_("couldn't check {source}: {error}", source=base, error=err))
    best: dict[str, Offer] = {}
    for offer in candidates:
        have = installed.get(offer.id)
        if have is None or version_key(offer.version) <= version_key(have):
            continue
        current = best.get(offer.id)
        if current is None or version_key(offer.version) > version_key(current.version):
            best[offer.id] = Offer(
                offer.id, have, offer.version, offer.source, offer.sha256, offer.where
            )
    return [best[k] for k in sorted(best)], notes


def _remote(base: str) -> list[Offer]:
    import urllib.request
    from urllib.parse import urljoin

    base = base if base.endswith("/") else base + "/"
    with urllib.request.urlopen(urljoin(base, CATALOG), timeout=20) as response:
        catalog = json.loads(response.read())
    offers: list[Offer] = []
    for entry in cast(list[JSON], catalog.get("packs") or []):
        item = cast(dict[str, JSON], entry)
        name = PurePosixPath(str(item.get("file") or "")).name
        if item.get("id") and item.get("version") and name.endswith(SUFFIX):
            offers.append(
                Offer(
                    str(item["id"]),
                    "",
                    str(item["version"]),
                    urljoin(base, name),
                    str(item.get("sha256") or ""),
                    base,
                )
            )
    return offers


def update(lib: PackLibrary, offer: Offer) -> Installed:
    """Install the newer version beside the installed one (campaigns keep their pins)."""
    if not offer.source.startswith(("https://", "http://")):
        return install(lib, offer.source, force=False)
    import urllib.request

    with tempfile.TemporaryDirectory(prefix="didact-update-") as scratch:
        download = Path(scratch) / f"{offer.id}-{offer.version}{SUFFIX}"
        try:
            with urllib.request.urlopen(offer.source, timeout=60) as response:
                download.write_bytes(response.read())
        except OSError as err:
            raise InvalidError(
                _("couldn't download {source}: {error}", source=offer.source, error=err),
                hint=_("check the connection and try again"),
            ) from err
        digest = hashlib.sha256(download.read_bytes()).hexdigest()
        if offer.sha256 and digest != offer.sha256:
            raise InvalidError(
                _("{file} doesn't match the hash its index gives", file=download.name),
                hint=_("it was changed or cut short: try again later"),
            )
        return install(lib, str(download), force=False)


def install(lib: PackLibrary, source: str, *, force: bool) -> Installed:
    """Install from a `.didactpack`, a pack folder, an https URL to a `.didactpack`, or the id
    of a pack that ships with Didact. A pack it needs that ships with Didact comes too."""
    ready = {s.id: s for s in shipped()}
    if source in ready and not Path(source).expanduser().exists():
        source = str(ready[source].path)
    with tempfile.TemporaryDirectory(prefix="didact-install-") as scratch:
        staged = _stage(source, Path(scratch))
        result = build(staged)
        if result.bundle is None:
            message = (
                _("this pack has problems: {problem}", problem=result.errors[0].text())
                if result.errors
                else _("this pack has problems: it doesn't build")
            )
            raise InvalidError(message, hint=_("ask its author for a fixed version"))
        manifest = cast(dict[str, JSON], result.bundle["manifest"])
        pack_id, version = str(manifest["id"]), str(manifest["version"])
        notes = _dependencies(lib, manifest, ready)
        notes += _requirements(lib, manifest)
        target = lib.installed_dir / pack_id / version
        if target.exists():
            if not force:
                raise ConflictError(
                    _("{pack} {version} is already installed", pack=pack_id, version=version),
                    hint=_("pass --force to replace it"),
                )
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(
            staged, target, ignore=shutil.ignore_patterns(INDEX, "__pycache__", ".build")
        )
    if manifest.get("plugins"):
        notes.append(
            _(
                "it has Python plugins, off until you trust them: `didact pack trust {pack}`",
                pack=pack_id,
            )
        )
    lib.refresh()
    return Installed(pack_id, version, target, notes)


def _dependencies(
    lib: PackLibrary, manifest: dict[str, JSON], ready: dict[str, Shipped]
) -> list[str]:
    """Install the packs this one needs that ship with Didact and aren't here yet."""
    from didact.packs.versions import parse_requirement, satisfies

    notes: list[str] = []
    requires = cast(dict[str, JSON], manifest.get("requires") or {})
    needs = [str(r) for r in cast(list[JSON], requires.get("packs") or [])]
    needs += [str(e) for e in cast(list[JSON], manifest.get("extends") or [])]
    for requirement in needs:
        dep_id, spec = parse_requirement(requirement)
        if any(satisfies(v.version, spec) for v in lib.available().get(dep_id, [])):
            continue
        dep = ready.get(dep_id)
        if dep is not None and satisfies(dep.version, spec):
            done = install(lib, str(dep.path), force=False)
            notes += [
                _(
                    "also installed {pack} {version}, which it needs",
                    pack=done.id,
                    version=done.version,
                ),
                *done.notes,
            ]
    return notes


def _stage(source: str, scratch: Path) -> Path:
    if source.startswith("git+") or source.endswith(".git") or ".git@" in source:
        return _clone(source.removeprefix("git+"), scratch / "pack")
    if source.startswith(("https://", "http://")):
        import urllib.request

        download = scratch / "download.didactpack"
        with urllib.request.urlopen(source, timeout=60) as response:
            download.write_bytes(response.read())
        return _unzip(download, scratch / "pack")
    path = Path(source).expanduser()
    if path.is_dir():
        if not (path / "pack.yaml").is_file():
            raise InvalidError(
                _("{folder} isn't a pack folder (no pack.yaml)", folder=path),
                hint=_("point at the folder that holds pack.yaml"),
            )
        staged = scratch / "pack"
        shutil.copytree(path, staged, ignore=shutil.ignore_patterns(".*", "__pycache__"))
        return staged
    if path.is_file():
        return _unzip(path, scratch / "pack")
    ready = ", ".join(s.id for s in shipped())
    hint = (
        _(
            "give a .didactpack file, a pack folder or an https URL, "
            "or a pack that ships with Didact: {packs}",
            packs=ready,
        )
        if ready
        else _("give a .didactpack file, a pack folder or an https URL")
    )
    raise InvalidError(_("can't find {source}", source=source), hint=hint)


def _clone(source: str, into: Path) -> Path:
    """`git+https://host/repo.git@v1.0` (or a local repo path): a shallow clone at the tag."""
    import subprocess

    tail = source.rpartition("/")[2]
    url, ref = (source.rpartition("@")[0], tail.rpartition("@")[2]) if "@" in tail else (source, "")
    command = ["git", "clone", "--depth", "1", *(["--branch", ref] if ref else []), url, str(into)]
    done = subprocess.run(command, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise InvalidError(
            _("git clone failed: {error}", error=done.stderr.strip()[:300]),
            hint=_("check the URL and tag"),
        )
    shutil.rmtree(into / ".git", ignore_errors=True)
    if not (into / "pack.yaml").is_file():
        raise InvalidError(
            _("that repository has no pack.yaml at its root"),
            hint=_("a pack repository keeps pack.yaml at its top level"),
        )
    return into


def _unzip(archive_path: Path, into: Path) -> Path:
    try:
        archive = zipfile.ZipFile(archive_path)
    except zipfile.BadZipFile as exc:
        raise InvalidError(
            _("{file} isn't a .didactpack (not a zip)", file=archive_path.name),
            hint=_("install a file made by `didact pack export`"),
        ) from exc
    with archive:
        if INDEX not in archive.namelist():
            raise InvalidError(
                _("{file} has no {index}", file=archive_path.name, index=INDEX),
                hint=_("export it with `didact pack export`"),
            )
        index = json.loads(archive.read(INDEX))
        expected = cast(dict[str, str], index.get("files") or {})
        for name in archive.namelist():
            clean = PurePosixPath(name)
            if clean.is_absolute() or ".." in clean.parts:
                raise InvalidError(
                    _("{file} has an unsafe path: {path}", file=archive_path.name, path=name),
                    hint=_("don't install it: it tries to write outside its folder"),
                )
        for name, digest in expected.items():
            if name not in archive.namelist():
                raise InvalidError(
                    _("{file} is missing {path}", file=archive_path.name, path=name),
                    hint=_("it's incomplete: get it again from its source"),
                )
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise InvalidError(
                    _("{path} doesn't match its hash: the file was changed or damaged", path=name),
                    hint=_("get it again from its source"),
                )
        extra = sorted(
            set(archive.namelist())
            - set(expected)
            - {INDEX}
            - {n for n in archive.namelist() if n.endswith("/")}
        )
        if extra:
            raise InvalidError(
                _(
                    "{file} has files not in its index: {paths}",
                    file=archive_path.name,
                    paths=", ".join(extra[:3]),
                ),
                hint=_("it was changed after it was exported: get it again from its source"),
            )
        archive.extractall(into)
    return into


def _requirements(lib: PackLibrary, manifest: dict[str, JSON]) -> list[str]:
    from didact.packs.versions import parse_requirement, satisfies

    notes: list[str] = []
    requires = cast(dict[str, JSON], manifest.get("requires") or {})
    wanted_didact = str(requires.get("didact") or "")
    if wanted_didact and not satisfies(__version__.split(".dev")[0], wanted_didact):
        notes.append(
            _(
                "it asks for Didact {wanted}; this is {version}",
                wanted=wanted_didact,
                version=__version__,
            )
        )
    available = lib.available()
    needs = [str(r) for r in cast(list[JSON], requires.get("packs") or [])]
    needs += [str(e) for e in cast(list[JSON], manifest.get("extends") or [])]
    for requirement in needs:
        dep_id, spec = parse_requirement(requirement)
        versions = available.get(dep_id, [])
        if not any(satisfies(v.version, spec) for v in versions):
            notes.append(
                _(
                    "it needs {requirement}, which isn't installed yet",
                    requirement=requirement.strip(),
                )
            )
    return notes


# ---------------------------------------------------------------------------- trust


def trust(lib: PackLibrary, pack: Pack) -> dict[str, str]:
    """Record the pack's plugin hashes as trusted. Any change to the code revokes it."""
    store = lib.trust_store()
    hashes = pack.plugin_hashes()
    store[f"{pack.id}@{pack.version}"] = {"plugins": dict[str, JSON](hashes), "trusted": now_iso()}
    atomic_write(lib.installed_dir / TRUST_FILE, json.dumps(store, indent=1))
    return hashes


def untrust(lib: PackLibrary, pack: Pack) -> bool:
    store = lib.trust_store()
    removed = store.pop(f"{pack.id}@{pack.version}", None) is not None
    atomic_write(lib.installed_dir / TRUST_FILE, json.dumps(store, indent=1))
    return removed


def content_hash(pack: Pack) -> str:
    """One hash for all of a pack's files: campaigns pin it."""
    digest = hashlib.sha256()
    for rel, file_hash in sorted(pack.files.items()):
        digest.update(f"{rel}:{file_hash}\n".encode())
    return digest.hexdigest()[:16]
