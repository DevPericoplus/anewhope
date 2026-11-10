"""El comando `curl | bash` que copia laimweb funciona pegado en un terminal.

QA 3.2.8 (usuario, 2026-11-10): sin comillas, el `&` de la URL manda curl a
segundo plano, la petición sale sin `platform` y el servidor responde 422.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.mark.parametrize("platform", ("mac_intel", "mac_silicon", "linux_deb", "linux_rpm"))
def test_script_command_quotes_the_url(platform: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from laim_web.adapters import laim_api_client

    monkeypatch.setattr(laim_api_client, "_get_laim_product_public_base_url", lambda: "https://www.laim.app")
    command = laim_api_client.get_laim_product_script_command("community_edition", platform)
    url = laim_api_client.get_laim_product_script_url("community_edition", platform)
    assert command == f'curl -fsSL "{url}" | bash'
    # A shell splits it into exactly: curl -fsSL <url> | bash — the URL whole.
    words = shlex.split(command)
    assert words[:3] == ["curl", "-fsSL", url]
    assert words[3:] == ["|", "bash"]
    assert f"platform={platform}" in words[2]


def test_installers_state_uses_the_quoted_command() -> None:
    state = (Path(__file__).resolve().parents[1] / "laim_web" / "laim_state.py").read_text(encoding="utf-8")
    assert "get_laim_product_script_command(" in state
    assert 'return f"curl -fsSL {url} | bash"' not in state
