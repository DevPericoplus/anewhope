#!/usr/bin/env python3
"""
Monitor de sesiones Redis para anewhope

Muestra información en tiempo real sobre las sesiones almacenadas en Redis.
"""
import redis
import json
from datetime import datetime
from typing import List, Dict, Any
import sys


class RedisSessionMonitor:
    """Monitor de sesiones en Redis"""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True
        )
    
    def get_all_sessions(self) -> List[str]:
        """Obtiene todas las keys de sesión"""
        return self.redis_client.keys("reflex:session:*")
    
    def get_session_data(self, session_key: str) -> Dict[str, Any]:
        """Obtiene los datos de una sesión específica"""
        data = self.redis_client.get(session_key)
        if data:
            return json.loads(data)
        return {}
    
    def get_session_ttl(self, session_key: str) -> int:
        """Obtiene el TTL (tiempo restante) de una sesión"""
        return self.redis_client.ttl(session_key)
    
    def print_session_info(self, session_key: str) -> None:
        """Imprime información formateada de una sesión"""
        data = self.get_session_data(session_key)
        ttl = self.get_session_ttl(session_key)
        
        print(f"\n{'='*80}")
        print(f"🔑 Session Key: {session_key}")
        print(f"⏱️  TTL: {ttl} segundos ({ttl//60} minutos)")
        print(f"{'='*80}")
        
        if not data:
            print("⚠️  Sesión vacía o expirada")
            return
        
        # Información del usuario
        print(f"\n👤 Usuario:")
        print(f"   ID: {data.get('user_id', 'N/A')}")
        print(f"   Nombre: {data.get('user_name', 'N/A')}")
        print(f"   Email: {data.get('user_email', 'N/A')}")
        print(f"   Organización ID: {data.get('organization_id', 'N/A')}")
        print(f"   Logueado: {'✅ Sí' if data.get('is_logged_in') else '❌ No'}")
        print(f"   Bloqueado: {'🔒 Sí' if data.get('is_blocked') else '✅ No'}")
        
        # Permisos críticos
        print(f"\n🔐 Permisos Críticos:")
        print(f"   training_create: {'✅' if data.get('can_training_create') else '❌'}")
        print(f"   user_create: {'✅' if data.get('can_user_create') else '❌'}")
        print(f"   org_create: {'✅' if data.get('can_org_create') else '❌'}")
        print(f"   project_create: {'✅' if data.get('can_project_create') else '❌'}")
        
        # Acceso a backoffice
        can_access_backoffice = data.get('can_training_create', False)
        print(f"\n🔧 Acceso Backoffice: {'✅ SÍ' if can_access_backoffice else '❌ NO'}")
        
        # Tokens
        print(f"\n🎫 Tokens:")
        access_token = data.get('access_token', '')
        print(f"   Access Token: {access_token[:20]}..." if access_token else "   Access Token: N/A")
        print(f"   Session ID: {data.get('session_id', 'N/A')}")
        
        # Metadata
        print(f"\n📊 Metadata:")
        print(f"   App actual: {data.get('current_app', 'N/A')}")
        print(f"   Login: {data.get('login_timestamp', 'N/A')}")
        print(f"   Última actividad: {data.get('last_activity', 'N/A')}")
        print(f"   IP: {data.get('ip_address', 'N/A')}")
    
    def monitor_all(self) -> None:
        """Monitorea todas las sesiones activas"""
        sessions = self.get_all_sessions()
        
        print(f"\n{'='*80}")
        print(f"📊 MONITOR DE SESIONES REDIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        print(f"\n✅ Sesiones activas: {len(sessions)}")
        
        if not sessions:
            print("\n⚠️  No hay sesiones activas")
            return
        
        for session_key in sessions:
            self.print_session_info(session_key)
        
        print(f"\n{'='*80}")
    
    def monitor_continuously(self, interval: int = 5) -> None:
        """Monitorea continuamente las sesiones"""
        import time
        
        print("🔄 Iniciando monitor continuo (Ctrl+C para salir)...")
        print(f"   Intervalo: {interval} segundos\n")
        
        try:
            while True:
                self.monitor_all()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n👋 Monitor detenido")
    
    def cleanup_expired(self) -> int:
        """Limpia sesiones expiradas manualmente"""
        sessions = self.get_all_sessions()
        cleaned = 0
        
        for session_key in sessions:
            ttl = self.get_session_ttl(session_key)
            if ttl <= 0:
                self.redis_client.delete(session_key)
                cleaned += 1
        
        return cleaned


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Monitor de sesiones Redis para anewhope"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host de Redis (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=6379,
        help="Puerto de Redis (default: 6379)"
    )
    parser.add_argument(
        "--db",
        type=int,
        default=0,
        help="Base de datos Redis (default: 0)"
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Monitoreo continuo"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Intervalo en segundos para monitoreo continuo (default: 5)"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Limpiar sesiones expiradas"
    )
    
    args = parser.parse_args()
    
    try:
        monitor = RedisSessionMonitor(
            host=args.host,
            port=args.port,
            db=args.db
        )
        
        if args.cleanup:
            print("🧹 Limpiando sesiones expiradas...")
            cleaned = monitor.cleanup_expired()
            print(f"✅ {cleaned} sesiones eliminadas")
        elif args.continuous:
            monitor.monitor_continuously(interval=args.interval)
        else:
            monitor.monitor_all()
    
    except redis.ConnectionError:
        print("❌ Error: No se puede conectar a Redis")
        print(f"   Asegúrate de que Redis esté corriendo en {args.host}:{args.port}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
