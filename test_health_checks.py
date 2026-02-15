#!/usr/bin/env python3
"""Script de prueba para verificar health checks de todos los servicios."""

import urllib.request
import urllib.error
import json
import os
import ssl

def test_service(name: str, url: str, accept_404: bool = False, accept_auth_errors: bool = False, skip_ssl_verify: bool = False):
    """Prueba un servicio y muestra el resultado."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    try:
        request = urllib.request.Request(url, method="GET")

        # Configurar SSL context si es necesario
        kwargs = {"timeout": 5}
        if skip_ssl_verify and url.startswith("https"):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            kwargs["context"] = ssl_context

        with urllib.request.urlopen(request, **kwargs) as response:
            status = response.status
            body = response.read().decode('utf-8')[:500]
            print(f"✅ Status: {status}")
            print(f"Body preview: {body}")
            return True
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read().decode('utf-8')[:500] if exc.fp else "No body"

        if accept_404 and status == 404:
            print(f"✅ Status: {status} (404 aceptado para este servicio)")
            return True
        elif accept_auth_errors and status in [401, 403]:
            print(f"✅ Status: {status} (Auth error aceptado - servidor alcanzable)")
            return True
        else:
            print(f"❌ HTTP Error: {status}")
            print(f"Body: {body}")
            return False
    except urllib.error.URLError as exc:
        print(f"❌ URL Error: {exc.reason}")
        return False
    except Exception as exc:
        print(f"❌ Exception: {exc}")
        return False


def main():
    print("\n" + "="*60)
    print("HEALTH CHECK TEST - ANEWHOPE MVP")
    print("="*60)

    results = {}

    # Frontend
    results['Frontend'] = test_service(
        "Frontend (Reflex)",
        "http://localhost:8005/",
        accept_404=True
    )

    # Backoffice
    results['Backoffice'] = test_service(
        "Backoffice (Reflex)",
        "http://localhost:8006/",
        accept_404=True
    )

    # Middleware
    results['Middleware'] = test_service(
        "Middleware (FastAPI)",
        "http://localhost:8007/docs"
    )

    # Backend Core
    results['Backend Core'] = test_service(
        "Backend Core (FastAPI)",
        "http://localhost:8003/docs"
    )

    # Broker
    results['Broker'] = test_service(
        "Broker (FastAPI)",
        "http://localhost:8008/docs"
    )

    # Trainer
    results['Trainer'] = test_service(
        "Trainer (FastAPI)",
        "http://localhost:8004/docs"
    )

    # fmanagement
    results['fmanagement'] = test_service(
        "fmanagement (Go)",
        "http://localhost:1666/",
        accept_404=True
    )

    # ChromaDB
    results['ChromaDB'] = test_service(
        "ChromaDB",
        "http://localhost:8100/api/v2/heartbeat"
    )

    # Ollama (via middleware)
    results['Ollama'] = test_service(
        "Ollama (via middleware)",
        "http://localhost:8007/trainer/ollama/health"
    )

    # SMS API
    sms_url = os.environ.get("SMS_API_URL", "https://pdy6d3.api.infobip.com")
    results['SMS API'] = test_service(
        "SMS API (Infobip)",
        sms_url,
        accept_auth_errors=True,
        skip_ssl_verify=True
    )

    # Resumen
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for service, passed_test in results.items():
        status = "✅ PASS" if passed_test else "❌ FAIL"
        print(f"{service:20s} {status}")

    print(f"\nTotal: {passed}/{total} servicios operativos")
    print("="*60)


if __name__ == "__main__":
    main()
