# Fases y tiers

## Mapa fase → tier de modelos

Define qué modelo (tier) se utiliza en cada fase del flujo conversacional y de agentes autónomos del cliente LAIM.

### Fases típicas

| Fase | Tier sugerido | Notas |
|------|---------------|-------|
| Respuesta rápida | Fast | Consultas cortas, baja latencia |
| Análisis medio | Medium | Razonamiento intermedio |
| Tareas complejas | Slow | Documentos largos, RAG profundo |

> Corresponde al mapa `phase_model_tiers` del cliente. La edición desde el portal permitirá despliegues homogéneos en equipos de la organización.
