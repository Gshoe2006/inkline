"""Getting work back after Inkline closes unexpectedly.

While there's unsaved work that isn't remembered anywhere else (photos, a booklet built page by page, or an
open project with changes), the window keeps a copy of it, at most once a minute, as an ordinary project
file in the settings folder. Closing Inkline or saving the project removes it, so a copy found at the next
start is work from a session that didn't close properly.

Each running Inkline names its copy after a session id of its own, and holds a lock on a file beside it for as
long as it runs. A copy whose lock nobody holds was left by a session that has ended; one whose lock is held
belongs to another Inkline open now, and is left alone. (Process numbers can't tell them apart: each Flatpak
runs in its own sandbox, where they repeat.)
"""

import glob
import os
import threading
import time
import sys
import traceback
import uuid
from datetime import datetime

from . import config, project

PREFIX = "recovery-"
SESSION = uuid.uuid4().hex[:12]
_held = {}               # lock file path -> the open lock file this process holds on it


# A lock held for as long as the session runs, released by the system however the process ends: flock on
# Linux, a locked byte (msvcrt) on Windows. Both raise BlockingIOError when another process holds it.
if os.name == "nt":
    import msvcrt

    def _lock(f):
        f.seek(0)
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as e:
            raise BlockingIOError(str(e)) from None

    def _unlock(f):
        f.seek(0)
        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
else:
    import fcntl

    def _lock(f):
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)

    def _unlock(f):
        fcntl.flock(f, fcntl.LOCK_UN)


def path_for(session=None):
    return os.path.join(config.config_dir(), f"{PREFIX}{session or SESSION}.{project.EXT}")


def _lock_path(path):
    return path[:-len(project.EXT)] + "lock"


def hold():
    """Hold this session's lock while it runs (released by the system however the process ends)."""
    lock = _lock_path(path_for())
    if lock in _held:
        return
    os.makedirs(config.config_dir(), exist_ok=True)
    f = open(lock, "w")
    _lock(f)
    _held[lock] = f


def release():
    """Closing properly: let go of this session's lock and remove its file."""
    while _held:
        lock, f = _held.popitem()
        f.close()            # closed first: Windows won't remove a file that's still open
        try:
            os.remove(lock)
        except OSError:
            pass


def _ended(path):
    """Whether the session that wrote this copy has ended (nobody holds its lock)."""
    if os.path.basename(path) == os.path.basename(path_for()):
        return False
    try:
        with open(_lock_path(path), "a") as f:
            _lock(f)
            _unlock(f)
        return True
    except BlockingIOError:
        return False
    except OSError:
        return True


def leftovers():
    """Copies left by sessions that didn't close properly, newest first. Lock files of sessions that ended
    with nothing to recover are tidied away."""
    folder = config.config_dir()
    for tmp in glob.glob(os.path.join(folder, f"{PREFIX}*.{project.EXT}.tmp")):   # a copy cut off mid-write
        if _ended(tmp[:-len(".tmp")]):
            try:
                os.remove(tmp)
            except OSError:
                pass
    for lock in glob.glob(os.path.join(folder, f"{PREFIX}*.lock")):
        copy = lock[:-len("lock")] + project.EXT
        if not os.path.exists(copy) and _ended(copy):
            try:
                os.remove(lock)
            except OSError:
                pass
    found = [p for p in glob.glob(os.path.join(folder, f"{PREFIX}*.{project.EXT}")) if _ended(p)]
    return sorted(found, key=os.path.getmtime, reverse=True)


def describe(path, data):
    """"14:32 · Maya's book · 12 pages · 3 photos": what a copy holds, for the question asking to recover it."""
    when = datetime.fromtimestamp(os.path.getmtime(path))
    today = datetime.now().date()
    parts = [when.strftime("%H:%M") if when.date() == today else when.strftime("%d %b, %H:%M")]
    src = (data.get("recovery") or {}).get("project")
    parts.append(project.title(src) if isinstance(src, str) and src else "untitled work")
    settings = data.get("settings") or {}
    pages = settings.get("page_list") or settings.get("pageList") or []
    if isinstance(pages, list) and pages:
        parts.append(f"{len(pages)} page{'s' if len(pages) != 1 else ''}")
    photos = data.get("photos") or []
    if isinstance(photos, list) and photos:
        parts.append(f"{len(photos)} photo{'s' if len(photos) != 1 else ''}")
    return " · ".join(parts)


def discard(path=None):
    path = path or path_for()
    try:
        os.remove(path)
    except OSError:
        pass
    if path != path_for():   # another session's copy, handled: its lock file goes too
        try:
            os.remove(_lock_path(path))
        except OSError:
            pass


class Keeper:
    """Writes this session's copy on a worker thread, one at a time; a newer copy replaces one not yet written."""

    def __init__(self, version):
        self.version = version
        try:
            hold()
            self.enabled = True
        except OSError:      # no lock (an odd filesystem): without one, another Inkline would take this one's
            self.enabled = False   # copy for a crash's and remove it, so no copies are kept at all
        self._lock = threading.Lock()
        self._next = None
        self._running = False
        self._gen = 0          # bumped by forget(): a copy being written when the work was saved is thrown away
        self._thread = None

    def keep(self, snapshot, source, extra=None):
        """Write a copy of snapshot (soon, on a thread). source: the project it came from; extra: more keys for
        the copy (the class set, as a project keeps it)."""
        if not self.enabled:
            return
        with self._lock:
            self._next = (snapshot, source, self._gen, dict(extra or {}))
            start = not self._running
            self._running = True
        if start:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def forget(self):
        """No copy is needed (closed properly, saved, or nothing worth keeping): remove it."""
        with self._lock:
            self._next = None
            self._gen += 1
        discard()

    def finish(self, wait=3.0):
        """Closing: let a copy being written finish (so no half-written file is left), then remove it."""
        with self._lock:
            self._next = None
            self._gen += 1
            thread = self._thread
        if thread is not None:
            thread.join(wait)
        discard()

    @property
    def idle(self):
        with self._lock:
            return not self._running and self._next is None

    def _loop(self):
        while True:
            with self._lock:
                job, self._next = self._next, None
                if job is None:
                    self._running = False
                    return
            snapshot, source, gen, extra = job
            try:
                os.makedirs(config.config_dir(), exist_ok=True)
                project.save(path_for(), snapshot, self.version,
                             {**extra, "recovery": {"project": source, "saved": time.time()}})
            except Exception:     # noqa: BLE001 — no copy this time (the work itself is untouched); the next
                if not isinstance(sys.exc_info()[1], OSError):   # change tries again, so this thread goes on
                    traceback.print_exc()
                continue
            with self._lock:
                stale = gen != self._gen
            if stale:             # saved or closed while this was being written
                discard()
