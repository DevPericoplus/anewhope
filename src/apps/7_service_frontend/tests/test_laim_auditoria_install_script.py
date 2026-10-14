"""La URL embebida del install-script marca source=install-script."""

from pathlib import Path

_ROUTER = (
    Path(__file__).resolve().parents[1] / "routermiddleware.py"
).read_text(encoding="utf-8")
_APIFE = (Path(__file__).resolve().parents[1] / "apife.py").read_text(encoding="utf-8")


def test_install_script_download_url_marks_source() -> None:
    assert "&source=install-script" in _ROUTER
    assert "def record_laim_auditoria_instalador" in _ROUTER


def test_install_script_and_download_record_auditoria() -> None:
    assert '"accion": "script_http"' in _APIFE
    assert 'source == "install-script"' in _APIFE
    assert "/laim/auditoria/heartbeat" in _APIFE
    assert "/laim/auditoria/instaladores" in _APIFE
