#!/usr/bin/env python3
"""
Genera nginx.conf dinámicamente según el entorno activo.

Este script lee las variables del entorno (public_name, private_name) desde
env.yaml y genera una configuración de nginx apropiada para dev/pre/pro.

Uso:
    python generate_nginx_conf.py [--environment ENV]

Ejemplos:
    python generate_nginx_conf.py --environment dev
    python generate_nginx_conf.py  # Usa el entorno definido en .envglobal
"""
import argparse
import sys
from pathlib import Path

# Add src/2_shared_application to path to import env_settings
project_root = Path(__file__).resolve().parents[4]
shared_app_path = project_root / "src" / "2_shared_application"
sys.path.insert(0, str(shared_app_path))

try:
    from config import env_settings
except ImportError:
    print("[ERROR] No se pudo importar env_settings. Verifica la estructura del proyecto.")
    sys.exit(1)


def get_environment_config(environment: str | None = None) -> dict[str, str]:
    """
    Obtiene la configuración del entorno desde env.yaml.

    Args:
        environment: Nombre del entorno (dev, pre, pro) o None para usar el activo

    Returns:
        dict con: public_name, private_name, environment
    """
    # Si se especifica un entorno, temporalmente cambiar la variable de entorno
    if environment:
        import os
        original_env = os.environ.get("ENVIRONMENT")
        os.environ["ENVIRONMENT"] = environment

    try:
        public_name = env_settings.get_env_value("public_name", "localhost")
        private_name = env_settings.get_env_value("private_name", "localhost")
        current_env = env_settings.get_env_value("ENVIRONMENT", "dev")

        return {
            "public_name": public_name,
            "private_name": private_name,
            "environment": current_env,
        }
    finally:
        # Restaurar entorno original si fue cambiado
        if environment and original_env:
            os.environ["ENVIRONMENT"] = original_env
        elif environment:
            os.environ.pop("ENVIRONMENT", None)


def generate_nginx_config(config: dict[str, str], ssl_enabled: bool = False) -> str:
    """
    Genera el contenido de nginx.conf basado en la configuración del entorno.

    Args:
        config: Diccionario con public_name, private_name, environment
        ssl_enabled: Si se debe incluir configuración SSL/HTTPS

    Returns:
        str: Contenido completo del nginx.conf
    """
    public_name = config["public_name"]
    environment = config["environment"]

    # En producción, forzar HTTPS
    force_https = environment in ["pre", "pro"]

    nginx_conf = f"""worker_processes  auto;

events {{
    worker_connections  1024;
}}

http {{
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;
    sendfile      on;
    keepalive_timeout 65;

    # Logging
    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log warn;

"""

    if ssl_enabled:
        nginx_conf += """    # Configuración SSL
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

"""

    # Servidor HTTP
    nginx_conf += f"""    # Servidor HTTP (puerto 80)
    server {{
        listen 80;
        server_name {public_name} *.{public_name};

"""

    if force_https:
        nginx_conf += """        # Redirigir todo el tráfico HTTP a HTTPS en pre/pro
        return 301 https://$host$request_uri;
    }

"""
    else:
        # Configuración completa para HTTP en dev
        nginx_conf += """        # Frontend principal
        location / {
            proxy_pass http://web_frontend:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support (CRÍTICO para Reflex)
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        # WebSocket endpoint de Reflex (frontend)
        location /_event {
            proxy_pass http://web_frontend:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        # API endpoint de Reflex (frontend)
        location /api {
            proxy_pass http://web_frontend:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backoffice
        location /backoffice/ {
            proxy_pass http://web_backoffice:8006/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        # WebSocket endpoint de Reflex (backoffice)
        location /backoffice/_event {
            proxy_pass http://web_backoffice:8006/_event;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }

        # API endpoint de Reflex (backoffice)
        location /backoffice/api {
            proxy_pass http://web_backoffice:8006/api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

"""

    if ssl_enabled:
        nginx_conf += f"""    # Servidor HTTPS (puerto 443)
    server {{
        listen 443 ssl;
        server_name {public_name} *.{public_name};

        # Certificados SSL
        ssl_certificate /etc/nginx/ssl/{public_name}.crt;
        ssl_certificate_key /etc/nginx/ssl/{public_name}.key;

        # Headers de seguridad
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;

        # Frontend principal
        location / {{
            proxy_pass http://web_frontend:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }}

        # WebSocket endpoint de Reflex (frontend)
        location /_event {{
            proxy_pass http://web_frontend:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }}

        # API endpoint de Reflex (frontend)
        location /api {{
            proxy_pass http://web_frontend:8005;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}

        # Backoffice
        location /backoffice/ {{
            proxy_pass http://web_backoffice:8006/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }}

        # WebSocket endpoint de Reflex (backoffice)
        location /backoffice/_event {{
            proxy_pass http://web_backoffice:8006/_event;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }}

        # API endpoint de Reflex (backoffice)
        location /backoffice/api {{
            proxy_pass http://web_backoffice:8006/api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }}
    }}

"""

    nginx_conf += "}\n"
    return nginx_conf


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(
        description="Genera nginx.conf dinámicamente según el entorno"
    )
    parser.add_argument(
        "--environment",
        "-e",
        choices=["dev", "pre", "pro"],
        help="Entorno específico (si no se especifica, usa el activo)",
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        help="Incluir configuración SSL/HTTPS (recomendado para pre/pro)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).parent / "nginx.conf",
        help="Archivo de salida (default: nginx.conf en el mismo directorio)",
    )

    args = parser.parse_args()

    # Obtener configuración del entorno
    print(f"[INFO] Obteniendo configuración del entorno...")
    config = get_environment_config(args.environment)

    print(f"[INFO] Entorno: {config['environment']}")
    print(f"[INFO] Dominio público: {config['public_name']}")
    print(f"[INFO] Dominio privado: {config['private_name']}")

    # Generar configuración
    print(f"[INFO] Generando nginx.conf...")
    nginx_content = generate_nginx_config(config, ssl_enabled=args.ssl)

    # Escribir archivo
    args.output.write_text(nginx_content)
    print(f"[OK] nginx.conf generado exitosamente: {args.output}")

    # Mostrar advertencias según el entorno
    if config["environment"] in ["pre", "pro"] and not args.ssl:
        print("")
        print("[WARN] Estás generando configuración para PRE/PRO sin SSL.")
        print("[WARN] Se recomienda usar --ssl y configurar certificados SSL válidos.")
        print("[WARN] Ejemplo: python generate_nginx_conf.py --ssl")

    print("")
    print("Próximos pasos:")
    print("  1. Revisar el archivo generado")
    print("  2. Si usas SSL, configurar certificados en /etc/nginx/ssl/")
    print("  3. Reiniciar nginx: docker-compose restart nginx")


if __name__ == "__main__":
    main()
