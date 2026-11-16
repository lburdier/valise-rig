# SPDX-License-Identifier: GPL-3.0-or-later
"""Automatic updates from the GitHub releases of the add-on.

* At start-up (at most once a day) a background thread asks the GitHub API for the latest release.
* If it is newer than the installed version, its .zip asset (the extension package) is downloaded and installed
  with Blender's own extension installer, either automatically  or with one click.
* Respects Blender's "Allow Online Access" setting; nothing is sent but a plain GET request.
Publishing a version = create a GitHub release tagged vX.Y.Z with the extension zip attached.
"""
import hashlib
import json
import os
import tempfile
import threading
import time
import urllib.error
import urllib.request

import bpy

PKG_ID = "valise_rig"
DEFAULT_REPO = "lburdier/valise-rig"
_UA = "Valise-Rig-Blender-Updater"
_DAY = 24 * 3600

state = {"status": "idle", "latest": "", "asset": None, "page": "", "notes": "", "error": "", "checked": 0.0,
         "auto": False}
_lock = threading.Lock()


# ------------------------------------------------------------------------------------------- helpers
def _vtuple(text):
    out = []
    for part in str(text).lstrip("vV").split("."):
        num = ""
        for ch in part:
            if not ch.isdigit():
                break
            num += ch
        out.append(int(num or 0))
    while len(out) < 3:
        out.append(0)
    return tuple(out[:3])


_VERSION = None


def current_version():
    global _VERSION
    if _VERSION is None:
        try:
            import tomllib
            with open(os.path.join(os.path.dirname(__file__), "blender_manifest.toml"), "rb") as f:
                _VERSION = _vtuple(tomllib.load(f)["version"])
        except Exception:
            _VERSION = (0, 0, 0)
    return _VERSION


def current_version_str():
    return ".".join(str(x) for x in current_version())


def _prefs():
    try:
        return bpy.context.preferences.addons[__package__].preferences
    except Exception:
        return None


def repo():
    p = _prefs()
    r = (getattr(p, "update_repo", "") or "").strip().strip("/") if p else ""
    if r.startswith("https://github.com/"):
        r = r[len("https://github.com/"):]
    return r or DEFAULT_REPO


def repo_url():
    return "https://github.com/" + repo()


def online_allowed():
    return bool(getattr(bpy.app, "online_access", True))


def install_kind():
    """('local' | 'remote' | 'legacy', repo module, repo index)."""
    parts = (__package__ or "").split(".")
    if len(parts) < 3 or parts[0] != "bl_ext":
        return "legacy", None, -1
    module = parts[1]
    for i, r in enumerate(bpy.context.preferences.extensions.repos):
        if r.module == module:
            return ("remote" if r.use_remote_url else "local"), module, i
    return "legacy", None, -1


def _stamp_path():
    try:
        d = bpy.utils.extension_path_user(__package__, path="", create=True)
    except Exception:
        d = tempfile.gettempdir()
    return os.path.join(d, "update_check.json")


def _last_check():
    try:
        with open(_stamp_path()) as f:
            return float(json.load(f).get("t", 0.0))
    except Exception:
        return 0.0


def _save_check(t):
    try:
        with open(_stamp_path(), "w") as f:
            json.dump({"t": t, "latest": state.get("latest", "")}, f)
    except Exception:
        pass


def tag_redraw():
    try:
        for w in bpy.context.window_manager.windows:
            for a in w.screen.areas:
                if a.type in {'VIEW_3D', 'PREFERENCES'}:
                    a.tag_redraw()
    except Exception:
        pass


# ------------------------------------------------------------------------------------------- check
def _fetch_latest(name):
    url = "https://api.github.com/repos/%s/releases/latest" % name
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        rel = json.loads(resp.read(4 * 1024 * 1024).decode("utf-8"))
    assets = [a for a in rel.get("assets", []) if a.get("name", "").lower().endswith(".zip")]
    # prefer the extension package (valise_rig-X.Y.Z.zip) over any other zip
    assets.sort(key=lambda a: (not a["name"].lower().startswith(PKG_ID), a["name"]))
    return dict(tag=rel.get("tag_name", ""), page=rel.get("html_url", ""), notes=(rel.get("body") or "")[:2000],
                asset=assets[0] if assets else None)


def _check_thread(name):
    try:
        rel = _fetch_latest(name)
        newer = _vtuple(rel["tag"]) > current_version() and current_version() != (0, 0, 0)
        with _lock:
            state.update(checked=time.time(), latest=rel["tag"].lstrip("vV"), page=rel["page"], notes=rel["notes"],
                         asset=rel["asset"], error="")
            if newer and rel["asset"] is None:
                state.update(status="error", error="release %s has no .zip file" % rel["tag"])
            else:
                state["status"] = "available" if newer else "uptodate"
    except urllib.error.HTTPError as exc:
        with _lock:
            state.update(status="error", checked=time.time(),
                         error=("no release published yet" if exc.code == 404 else "GitHub: HTTP %d" % exc.code))
    except Exception as exc:  # noqa: BLE001 (offline, DNS, timeout...)
        with _lock:
            state.update(status="error", error=str(exc)[:160], checked=time.time())


def check(manual=False, auto_install=False):
    """Start a background check. Returns an error message for the UI, or ''."""
    if state["status"] in ("checking", "downloading", "installing"):
        return ""
    if not online_allowed():
        state.update(status="offline")
        return "Online access is disabled in Blender's preferences (System > Network)"
    state.update(status="checking", auto=auto_install, error="")
    threading.Thread(target=_check_thread, args=(repo(),), daemon=True, name="valise-update-check").start()
    if not bpy.app.timers.is_registered(_poll):
        bpy.app.timers.register(_poll, first_interval=0.5, persistent=True)
    return ""


def _flying():
    return False


def _poll():
    st = state["status"]
    if st in ("checking", "downloading"):
        return 0.5
    if st in ("available", "uptodate"):
        _save_check(state["checked"])
    tag_redraw()
    if st == "available" and state["auto"]:
        if _flying():
            return 5.0
        state["auto"] = False
        install()
        return 0.5 if state["status"] == "downloading" else None
    if st == "downloaded":
        _install_downloaded()
    return None


# ------------------------------------------------------------------------------------------- install
def _download_thread(asset, version):
    try:
        req = urllib.request.Request(asset["browser_download_url"], headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read(64 * 1024 * 1024)
        size = asset.get("size")
        if size and int(size) != len(data):
            raise ValueError("wrong file size")
        digest = str(asset.get("digest") or "")
        if digest.startswith("sha256:") and hashlib.sha256(data).hexdigest() != digest[7:]:
            raise ValueError("wrong checksum")
        folder = tempfile.mkdtemp(prefix="valise_update_")
        path = os.path.join(folder, "%s-%s.zip" % (PKG_ID, version))
        with open(path, "wb") as fh:
            fh.write(data)
        with _lock:
            state.update(status="downloaded", download=path)
    except Exception as exc:  # noqa: BLE001
        with _lock:
            state.update(status="error", error="download: %s" % str(exc)[:140])


def install():
    """Install the latest release. Returns an error message for the UI, or ''."""
    if _flying():
        return "Update not possible right now"
    asset = state.get("asset")
    if not asset or state["status"] not in ("available", "error"):
        return "No update available"
    kind, _module, _index = install_kind()
    if kind == "legacy":
        import webbrowser
        webbrowser.open(state.get("page") or repo_url())
        return "Legacy add-on install: download the new version from the page that just opened"
    state["status"] = "downloading"
    threading.Thread(target=_download_thread, args=(asset, state.get("latest", "")), daemon=True,
                     name="valise-update-dl").start()
    if not bpy.app.timers.is_registered(_poll):
        bpy.app.timers.register(_poll, first_interval=0.5, persistent=True)
    return ""


def _call_op(op, **kw):
    wm = bpy.context.window_manager
    win = wm.windows[0] if wm and len(wm.windows) else None
    if win is not None:
        with bpy.context.temp_override(window=win):
            return op(**kw)
    return op(**kw)


def _install_downloaded():
    # runs from a timer, outside any operator of this add-on: Blender reloads the add-on during the call
    path = state.get("download")
    _kind, module, _index = install_kind()
    state["status"] = "installing"
    try:
        os.environ["VALISE_UPDATED_FROM"] = "%s>%s" % (current_version_str(), state.get("latest", ""))
        res = _call_op(bpy.ops.extensions.package_install_files, filepath=path, repo=module,
                       enable_on_install=True, overwrite=True)
        if "FINISHED" not in res:
            raise RuntimeError("Blender refused the package (%s)" % ", ".join(sorted(res)))
        state["status"] = "installed"
    except Exception as exc:  # noqa: BLE001
        os.environ.pop("VALISE_UPDATED_FROM", None)
        state.update(status="error", error=str(exc)[:160])
    tag_redraw()


def updated_from():
    """('2.7.0', '2.8.0') right after an automatic update in this Blender session."""
    val = os.environ.get("VALISE_UPDATED_FROM", "")
    return tuple(val.split(">", 1)) if ">" in val else None


# ------------------------------------------------------------------------------------------- start-up
def _startup():
    p = _prefs()
    if p is None or not getattr(p, "check_updates", True) or not online_allowed():
        return None
    if time.time() - _last_check() < _DAY:
        return None
    check(auto_install=getattr(p, "auto_update", True))
    return None


def register():
    if bpy.app.background or os.environ.get("VALISE_NO_UPDATE_CHECK"):
        return
    # persistent: otherwise loading the .blend given on the command line removes the timer
    bpy.app.timers.register(_startup, first_interval=6.0, persistent=True)


def unregister():
    for fn in (_startup, _poll):
        if bpy.app.timers.is_registered(fn):
            bpy.app.timers.unregister(fn)
