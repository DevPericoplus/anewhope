#!/bin/bash
# Monitor all debug logs during training

echo "================================================================================"
echo "MONITOREANDO FLUJO DE ENTRENAMIENTO EN TIEMPO REAL"
echo "================================================================================"
echo ""
echo "Esperando que envíes un entrenamiento desde el backoffice..."
echo "Presiona Ctrl+C para detener el monitoreo"
echo ""

# Limpiar archivos de log previos
> /tmp/monitor_backoffice.log
> /tmp/monitor_middleware.log
> /tmp/monitor_broker.log
> /tmp/monitor_trainer.log

# Monitorear logs en paralelo
tail -f /tmp/backoffice_debug_full.log 2>/dev/null | while read line; do
    if echo "$line" | grep -q -E "BACKOFFICE API_CLIENT|SEND_TO_TRAINER|POLLING|id_entrenamiento"; then
        echo "[BACKOFFICE] $line"
    fi
done &
PID_BACKOFFICE=$!

tail -f /tmp/middleware_debug.log 2>/dev/null | while read line; do
    if echo "$line" | grep -q -E "MIDDLEWARE ENDPOINT|id_entrenamiento|collection_name"; then
        echo "[MIDDLEWARE] $line"
    fi
done &
PID_MIDDLEWARE=$!

tail -f /tmp/broker_fixed.log 2>/dev/null | while read line; do
    if echo "$line" | grep -q -E "BROKER ENDPOINT|BROKER->TRAINER|id_entrenamiento|collection_name"; then
        echo "[BROKER    ] $line"
    fi
done &
PID_BROKER=$!

tail -f /tmp/trainer.log 2>/dev/null | while read line; do
    if echo "$line" | grep -q -E "POST /trainer/entrenamientos|Entrenamiento.*registrado|id_entrenamiento|collection_name"; then
        echo "[TRAINER   ] $line"
    fi
done &
PID_TRAINER=$!

# Esperar y limpiar al salir
trap "kill $PID_BACKOFFICE $PID_MIDDLEWARE $PID_BROKER $PID_TRAINER 2>/dev/null; exit" SIGINT SIGTERM

wait
