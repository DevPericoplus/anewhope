"""El script público `curl -fsSL "<url>" | bash` instala LAIM de verdad.

QA 3.2.8 (usuario, 2026-11-10): ningún script copiado desde laimweb
funcionó. En Mac el script buscaba una `.app` dentro del DMG, pero el DMG de
LAIM trae `install-laim.sh`; en Linux usaba `sudo` aunque el usuario ya fuese
root y el .deb iba con `dpkg -i` + `apt-get install -f`. Estas pruebas ejecutan
el script generado con curl/hdiutil/sudo/apt-get/dnf falsos en el PATH: nada
se instala, pero se comprueba qué ejecutaría.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from routermiddleware import _laim_install_script_body

_URL = "https://example.invalid/laim/product/download?edition=community_edition&platform=x"
_PLATFORMS = ("mac_intel", "mac_silicon", "linux_deb", "linux_rpm")


def _fake(bin_dir: Path, name: str, body: str) -> None:
    path = bin_dir / name
    path.write_text("#!/bin/sh\n" + body, encoding="utf-8")
    path.chmod(0o755)


def _run(platform: str, filename: str, tmp_path: Path, uid: int, fakes: dict[str, str]):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "calls.log"
    _fake(bin_dir, "curl", 'out=""\nwhile [ $# -gt 0 ]; do [ "$1" = -o ] && out="$2"; shift; done\n'
          'echo payload > "$out"\n')
    _fake(bin_dir, "id", f'echo {uid}\n')
    for name, body in fakes.items():
        _fake(bin_dir, name, body)
    for tool in ("bash", "sh", "mktemp", "rm", "chmod", "mkdir", "cat", "dirname", "uname", "grep", "head", "cp", "sed", "ls"):
        found = shutil.which(tool)
        if found and not (bin_dir / tool).exists():
            (bin_dir / tool).symlink_to(found)
    script = _laim_install_script_body(platform, _URL, filename)
    env = {"PATH": str(bin_dir), "LOG": str(log), "HOME": str(tmp_path), "LANG": "es_ES.UTF-8"}
    result = subprocess.run(
        ["bash", "-s"], input=script, capture_output=True, text=True, env=env,
        timeout=30, start_new_session=True,
    )
    calls = log.read_text(encoding="utf-8") if log.exists() else ""
    return result, calls


@pytest.mark.parametrize("platform", _PLATFORMS)
def test_every_script_is_valid_bash(platform: str) -> None:
    script = _laim_install_script_body(platform, _URL, "f")
    check = subprocess.run(["bash", "-n"], input=script, capture_output=True, text=True)
    assert check.returncode == 0, check.stderr


@pytest.mark.parametrize("platform", ("mac_intel", "mac_silicon"))
def test_mac_script_runs_the_dmg_installer_not_an_app(platform: str, tmp_path: Path) -> None:
    hdiutil = (
        'echo "hdiutil $*" >> "$LOG"\n'
        'if [ "$1" = attach ]; then\n'
        '  mnt=""\n  while [ $# -gt 0 ]; do [ "$1" = -mountpoint ] && mnt="$2"; shift; done\n'
        '  mkdir -p "$mnt"\n'
        '  printf \'#!/bin/sh\\necho "helper $0" >> "$LOG"\\n\' > "$mnt/install-laim.sh"\n'
        'fi\n'
    )
    result, calls = _run(platform, "laim_install_3.2.8_x64.dmg", tmp_path, 501, {"hdiutil": hdiutil})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "helper " in calls and "install-laim.sh" in calls, calls
    assert "hdiutil detach" in calls, "the DMG must be detached after installing"
    assert "/Applications" not in result.stdout + result.stderr


def test_mac_script_fails_and_detaches_when_the_installer_fails(tmp_path: Path) -> None:
    hdiutil = (
        'echo "hdiutil $*" >> "$LOG"\n'
        'if [ "$1" = attach ]; then\n'
        '  mnt=""\n  while [ $# -gt 0 ]; do [ "$1" = -mountpoint ] && mnt="$2"; shift; done\n'
        '  mkdir -p "$mnt"\n  printf \'#!/bin/sh\\nexit 1\\n\' > "$mnt/install-laim.sh"\n'
        'fi\n'
    )
    result, calls = _run("mac_intel", "laim.dmg", tmp_path, 501, {"hdiutil": hdiutil})
    assert result.returncode != 0
    assert "hdiutil detach" in calls


@pytest.mark.parametrize("uid,want_sudo", ((0, False), (1000, True)))
def test_deb_script_uses_apt_with_the_file_and_sudo_only_when_needed(
    uid: int, want_sudo: bool, tmp_path: Path
) -> None:
    fakes = {
        "apt-get": 'echo "apt-get $*" >> "$LOG"\n',
        "sudo": 'echo "sudo $1" >> "$LOG"\n"$@"\n',
        "dpkg": 'echo "dpkg $*" >> "$LOG"\n',
    }
    result, calls = _run("linux_deb", "laim_install_3.2.8_amd64.deb", tmp_path, uid, fakes)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "apt-get install -y /" in calls and "laim_install_3.2.8_amd64.deb" in calls, calls
    assert "dpkg -i" not in calls
    assert ("sudo apt-get" in calls) is want_sudo, calls


@pytest.mark.parametrize("uid,want_sudo", ((0, False), (1000, True)))
def test_rpm_script_uses_dnf_and_sudo_only_when_needed(
    uid: int, want_sudo: bool, tmp_path: Path
) -> None:
    fakes = {
        "dnf": 'echo "dnf $*" >> "$LOG"\n',
        "sudo": 'echo "sudo $1" >> "$LOG"\n"$@"\n',
    }
    result, calls = _run("linux_rpm", "laim-install-3.2.8.x86_64.rpm", tmp_path, uid, fakes)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "dnf install -y /" in calls and "laim-install-3.2.8.x86_64.rpm" in calls, calls
    assert ("sudo dnf" in calls) is want_sudo, calls


def test_linux_script_explains_when_it_cannot_become_root(tmp_path: Path) -> None:
    result, calls = _run("linux_rpm", "laim.rpm", tmp_path, 1000, {"dnf": 'echo "dnf $*" >> "$LOG"\n'})
    assert result.returncode != 0
    assert "dnf" not in calls
    assert "root" in result.stderr


def test_script_does_not_print_its_own_success_line() -> None:
    # The package (or install-laim.sh) already says how to continue (laim init);
    # a second «laim instalado correctamente» after it is noise or, on error, false.
    for platform in _PLATFORMS:
        assert "laim instalado correctamente" not in _laim_install_script_body(platform, _URL, "f")
