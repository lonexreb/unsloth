# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2026-present the Unsloth AI Inc. team. All rights reserved. See /studio/LICENSE.AGPL-3.0

"""`update --local` must not destroy the install it runs from (#7697).

Windows locks the directory entry an image was launched from, so when the
update runs as the venv's own Scripts\\unsloth.exe, the transaction's
move-aside fails and no retry from this process or its children can free the
entry (#7740). A local update always reinstalls the unsloth package, and pip
uninstalls before it installs: it removes unsloth_cli, then dies on the locked
stub, and what is left is a launcher that starts and immediately raises
ModuleNotFoundError. The guard pinned here stops that run before setup touches
the environment, and names the managed-interpreter re-run that works.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _studio():
    from unsloth_cli.commands import studio as _studio_mod
    return _studio_mod


# ── the guard's own judgement ────────────────────────────────────────


def _blocked_transaction(studio, launcher: Path):
    """A transaction as __enter__ leaves it when the move-aside failed."""
    transaction = studio._WindowsLauncherUpdateTransaction()
    transaction.enabled = True
    transaction.launcher = launcher
    transaction.move_aside_error = OSError(32, "The process cannot access the file")
    return transaction


def test_the_guard_matches_this_process_own_entry(monkeypatch, tmp_path):
    studio = _studio()
    launcher = tmp_path / "Scripts" / "unsloth.exe"
    transaction = _blocked_transaction(studio, launcher)
    monkeypatch.setattr(sys, "argv", [str(launcher)])
    assert transaction.blocks_reinstall_of_running_launcher()


@pytest.mark.skipif(os.name != "nt", reason = "normcase only folds case on Windows")
def test_case_differences_are_path_identity_noise_on_windows(monkeypatch, tmp_path):
    studio = _studio()
    launcher = tmp_path / "Scripts" / "unsloth.exe"
    transaction = _blocked_transaction(studio, launcher)
    monkeypatch.setattr(sys, "argv", [str(launcher).upper()])
    assert transaction.blocks_reinstall_of_running_launcher()


def test_the_hardlinked_shim_is_a_different_entry(monkeypatch, tmp_path):
    # bin\unsloth.exe hardlinks the same file, but launching through the shim
    # locks the shim's entry and the Scripts entry stays movable: the guard
    # compares directory entries, never inodes.
    studio = _studio()
    scripts = tmp_path / "Scripts"
    scripts.mkdir(parents = True)
    launcher = scripts / "unsloth.exe"
    launcher.write_bytes(b"MZ fake")
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    shim = shim_dir / "unsloth.exe"
    try:
        os.link(launcher, shim)
    except OSError:
        shim.write_bytes(b"MZ fake")
    transaction = _blocked_transaction(studio, launcher)
    monkeypatch.setattr(sys, "argv", [str(shim)])
    assert not transaction.blocks_reinstall_of_running_launcher()


def test_the_guard_needs_a_failed_move(monkeypatch, tmp_path):
    studio = _studio()
    launcher = tmp_path / "Scripts" / "unsloth.exe"
    transaction = _blocked_transaction(studio, launcher)
    transaction.move_aside_error = None
    monkeypatch.setattr(sys, "argv", [str(launcher)])
    assert not transaction.blocks_reinstall_of_running_launcher()


def test_the_guard_is_windows_only(monkeypatch, tmp_path):
    studio = _studio()
    launcher = tmp_path / "Scripts" / "unsloth.exe"
    transaction = _blocked_transaction(studio, launcher)
    transaction.enabled = False
    monkeypatch.setattr(sys, "argv", [str(launcher)])
    assert not transaction.blocks_reinstall_of_running_launcher()


# ── what update does with that judgement ─────────────────────────────


class _BlockedLauncherUpdate:
    """The transaction as it stands after a move-aside the guard recognises."""

    launcher = Path("C:/users/u/.unsloth/studio/unsloth_studio/Scripts/unsloth.exe")

    def __enter__(self):
        return self

    def blocks_reinstall_of_running_launcher(self):
        return True

    def validate_launcher(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def _neutered(monkeypatch, transaction_class):
    studio = _studio()
    seen = {}
    monkeypatch.setattr(studio, "_ensure_studio_env_exported", lambda *a, **k: None)
    monkeypatch.setattr(studio, "_WindowsLauncherUpdateTransaction", transaction_class)
    monkeypatch.setattr(studio, "_refresh_desktop_shortcuts", lambda *a, **k: None)
    monkeypatch.setattr(studio, "_fail_if_install_damaged", lambda *a, **k: None, raising = False)
    monkeypatch.setattr(studio, "_run_setup_script", lambda *a, **k: seen.setdefault("setup", True))
    return studio, seen


def _checkout(tmp_path: Path) -> Path:
    checkout = tmp_path / "unsloth"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname = 'unsloth'\n")
    return checkout


def test_a_blocked_local_update_stops_before_setup(monkeypatch, tmp_path):
    studio, seen = _neutered(monkeypatch, _BlockedLauncherUpdate)
    monkeypatch.setenv("STUDIO_LOCAL_REPO", str(_checkout(tmp_path)))
    result = CliRunner().invoke(studio.studio_app, ["update", "--local"])
    assert result.exit_code == 1, result.output
    assert "setup" not in seen
    # The message must hand over the invocation that works: the managed
    # interpreter's entry is not the one this process locked.
    assert "python.exe" in result.output
    assert "studio update --local" in result.output


def test_a_blocked_pypi_update_still_runs(monkeypatch, tmp_path):
    # Without --local the reinstall is not guaranteed: setup's fallback leaves
    # unsloth at its old version rather than uninstalling over the locked stub,
    # and a no-op update from the venv copy completes today. Failing early here
    # would break a path that currently works (#7740's own first-cut mistake).
    studio, seen = _neutered(monkeypatch, _BlockedLauncherUpdate)
    result = CliRunner().invoke(studio.studio_app, ["update"])
    assert result.exit_code == 0, result.output
    assert seen.get("setup")
