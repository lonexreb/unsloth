# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""A file literally named ``nul`` in the session workdir must not read as a device node (#12473).

Git Bash writes ``> nul`` as a real file (MSYS opens names through the extended-length namespace), while
a plain Win32 ``lstat`` of that name resolves to the DOS device, so the workdir scan refused every
Python and Terminal call with "contains a device or IPC node" until the file was deleted by hand.
"""

from __future__ import annotations

import os
import stat
import sys
import types

from core.inference import os_sandbox


def _extended(path: str) -> str:
    return "\\\\?\\" + path if sys.platform == "win32" else path


def test_a_file_named_nul_in_the_workdir_is_an_ordinary_file(tmp_path):
    """On Windows this is the reporter's workdir; elsewhere ``nul`` is just a name and the scan was always clean."""
    workdir = tmp_path / "work"
    workdir.mkdir()
    with open(_extended(str(workdir / "nul")), "w") as handle:
        handle.write("")

    assert os_sandbox.scan_workdir_for_host_channels(str(workdir)) == ()


def test_the_scan_reads_a_dos_device_name_through_the_extended_length_path(monkeypatch, tmp_path):
    """Pins the mechanism on every platform: the entry is stat'ed by its ``\\\\?\\`` path, which reaches
    the file on disk, never by the plain path, which the Win32 namespace turns into the device."""
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "nul").write_text("")
    real_lstat = os.lstat

    def lstat(path, *args, **kwargs):
        path = os.fspath(path)
        extended = path.startswith("\\\\?\\")
        if extended:
            path = path[4:]
            if os.sep == "/":
                path = path.replace("\\", "/")
        info = real_lstat(path, *args, **kwargs)
        if os.path.basename(path).lower() != "nul":
            return info
        # The extended-length path reaches the file on disk; the plain one answers the NUL character device.
        mode = stat.S_IFREG | 0o644 if extended else stat.S_IFCHR | 0o666
        return os.stat_result((mode, *tuple(info)[1:]))

    monkeypatch.setattr(os_sandbox, "sys", types.SimpleNamespace(platform = "win32"))
    monkeypatch.setattr(os, "lstat", lstat)
    assert os_sandbox._host_channel_hazard(str(workdir), 1000, 5.0) is None
