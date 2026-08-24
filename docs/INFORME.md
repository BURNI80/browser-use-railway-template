# Informe de creación del template — Browser Use en Railway

Fecha: 2026-08-24. Estado: código y docs listos en local. Pendiente (requiere tu OK): crear repo GitHub, desplegar proyecto Railway, publicar template.

## Resumen de decisiones

### 1. Wrapper propio FastAPI en vez de "servidor oficial"
- browser-use (0.13.8) es hoy una **librería Python + CLI**; no publica un servidor REST self-hosted oficial. El issue upstream pidiendo imagen docker del API ([#658](https://github.com/browser-use/browser-use/issues/658)) se cerró como *not planned* (marzo 2026).
- Alternativa comunitaria `browser-use/web-ui` existe pero es otro repo grande con stack Gradio/FastAPI distinto y sin release estable — más superficie de fallo y menos control.
- Decisión: wrapper mínimo (~300 líneas) sobre la librería: `POST /api/runs`, `GET /api/runs[/{id}]`, `/health`, UI estática de una página, Swagger automático. Cumple el brief ("1 servicio exponiendo su API/UI") con superficie mínima y versiones pineadas.

### 2. Chromium desde apt Debian (no Playwright)
- Copia el enfoque del Dockerfile oficial upstream: paquete `chromium` de bookworm + fuentes, symlinks `chromium-browser`. Imagen reproducible, sin descargas de navegador en runtime.
- Flags de contenedor (`--no-sandbox`, shm, GPU off) los aplica la propia librería al detectar `IN_DOCKER=true` (verificado en `browser_use/config.py`).

### 3. Versiones pineadas
- Base `python:3.12-slim-bookworm`; `browser-use==0.13.8` (última en PyPI a día de hoy), `fastapi==0.141.1`, `uvicorn==0.52.4`. Nada de `:latest`.

### 4. Healthcheck siempre-verde
- `/health` responde 200 aunque falten API keys (con campo `providers_configured` informativo). Así el servicio no entra en crash-loop por falta de configuración y el usuario ve el aviso en la UI. Railway valida el deploy con este endpoint.

### 5. UX / configuración mínima (regla AGENTS.md)
- Único paso manual obligatorio: pegar **una** variable LLM. Se recomienda `GOOGLE_API_KEY` (Gemini free tier → coste total ~0 en plan Hobby).
- La UI detecta keys ausentes y muestra instrucciones con enlaces directos para conseguirlas.
- Sin BDs ni Redis → nada que conectar a mano.
- Auth opcional con `BU_API_TOKEN` (Railway puede generarlo); si está activo la UI pide el token una vez.

### 6. Persistencia y reglas de plataforma
- Volumen en `/data`: perfil Chromium persistente (logins sobreviven redeploys) + descargas. Cumple regla de filesystem efímero.
- Solo HTTP público; nada UDP; sin docker socket; puerto desde `$PORT`.
- `restartPolicyType=ON_FAILURE`, healthcheck timeout 300 s (build inicial pesado).

### 7. Cabida en capa gratuita/Hobby
- 1 solo servicio, sin DBs. Idle ~150–250 MB (~$1.5–3/mes). Con uso ligero cabe en los $5 de crédito. Documentado en README con tabla honesta.

## Desviaciones del brief

| Brief | Realidad | Impacto |
| --- | --- | --- |
| "~50k★" | 79k★+ (docs oficiales ago 2026) | Ninguno; a favor |
| "exponiendo su API/UI" implícita como algo existente | No existe servidor OSS oficial → wrapper propio documentado | Bajo; decisión explicada arriba |
| "~1 GB" RAM | Confirmado: idle <250 MB, picos ~0.7–1 GB con 1 tarea | Ninguno |

## Pendientes hasta publicación (bloqueados por tu OK)

1. Crear repo GitHub público y push (nombre sugerido: `browser-use-railway-template`).
2. Desplegar proyecto Railway desde el repo (MCP o dashboard), añadir volumen `/data`, generar dominio, probar end-to-end (tarea real con Gemini free tier).
3. Publicar como Template: nombre "Browser Use", categoría AI/Agents, icono 1:1, overview según `docs/TEMPLATE_OVERVIEW.md`.
4. Capturas de la app funcionando para este informe.
5. Aplicar a railway.com/partners (proyecto open source MIT).

## Riesgos conocidos

- La librería evoluciona rápido (0.x): el pin exacto evita sorpresas; revisión trimestral recomendada.
- Resultados en memoria: se pierden al redeploy (documentado). Para histórico, consumir la API desde apps propias.
- Sitios con anti-bot agresivo pueden bloquear Chromium headless casero (la solución oficial es Browser Use Cloud de pago; fuera de scope de esta template gratis).
