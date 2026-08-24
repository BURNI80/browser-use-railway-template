# Browser Use en Railway

Template self-hosted de [Browser Use](https://github.com/browser-use/browser-use) (79k+ estrellas): agentes de IA que manejan un navegador Chromium real como lo haría una persona — navegan, hacen clic, rellenan formularios y extraen datos.

Un solo servicio expone:

- **Web UI** para lanzar tareas en lenguaje natural y ver resultados.
- **API REST** (`POST /api/runs`, `GET /api/runs/{id}`) para integrar el agente en tus apps/n8n/Make/scripts.
- **Swagger** interactivo en `/docs`.
- **Healthcheck** en `/health` para Railway.

El navegador corre headless dentro del mismo contenedor. No necesita base de datos ni Redis.

---

## Tabla de contenidos

1. [Qué incluye](#qué-incluye)
2. [Despliegue](#despliegue)
3. [Configurar la clave LLM (único paso obligatorio)](#configurar-la-clave-llm-único-paso-obligatorio)
4. [Variables de entorno](#variables-de-entorno)
5. [Uso: UI, API y ejemplos](#uso-ui-api-y-ejemplos)
6. [Coste estimado](#coste-estimado)
7. [Persistencia](#persistencia)
8. [Seguridad](#seguridad)
9. [Troubleshooting](#troubleshooting)
10. [Licencias y créditos](#licencias-y-créditos)

---

## Qué incluye

| Servicio | Imagen | Función |
| --- | --- | --- |
| Browser Use | Dockerfile propio (Python 3.12-slim + Chromium Debian) | API + UI + agente con Chromium headless |

- Versiones fijadas: `browser-use==0.13.8`, `fastapi==0.141.1`, `uvicorn==0.52.4`.
- Healthcheck HTTP cada vez que Railway despliega o reinicia.
- Volumen montado en `/data` (perfil del navegador persistente).
- Sin dependencias externas (no Postgres, no Redis) = coste mínimo.

## Despliegue

1. Pulsa **Deploy on Railway** (botón del template).
2. Espera a que el build termine (~3–6 min la primera vez; instala Chromium).
3. Abre la URL pública `https://<tu-servicio>.up.railway.app`.
4. Sigue el aviso amarillo de la UI para pegar tu API key de un proveedor LLM (ver abajo).

## Configurar la clave LLM (único paso obligatorio)

El agente necesita un modelo de IA. Con **una sola variable** ya funciona:

| Proveedor | Variable | Dónde conseguir la key | Coste |
| --- | --- | --- | --- |
| Google Gemini (recomendado) | `GOOGLE_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) | **Free tier generoso** |
| Browser Use Cloud | `BROWSER_USE_API_KEY` | [cloud.browser-use.com/new-api-key](https://cloud.browser-use.com/new-api-key) | 5 tareas gratis, luego de pago |
| OpenAI | `OPENAI_API_KEY` | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | De pago |
| Anthropic | `ANTHROPIC_API_KEY` | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) | De pago |

Pasos exactos:

1. En tu proyecto Railway entra al servicio → pestaña **Variables**.
2. Añade `GOOGLE_API_KEY` con tu key de AI Studio (gratis).
3. Railway redespliega solo al guardar. Listo — la UI deja de mostrar el aviso.

Modelo por defecto si hay varias keys: primero Google, luego Browser Use, OpenAI, Anthropic. Cámbialo con `BU_DEFAULT_MODEL` (ej.: `openai/gpt-4.1-mini`).

## Variables de entorno

| Variable | Obligatoria | Por defecto | Descripción |
| --- | --- | --- | --- |
| `GOOGLE_API_KEY` | Una LLM sí* | — | Key de Google AI Studio. Free tier. |
| `BROWSER_USE_API_KEY` | opcional | — | Modelos optimizados bu-* de Browser Use Cloud. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | opcional | — | Otros proveedores soportados. |
| `BU_DEFAULT_MODEL` | no | auto | Modelo por defecto, ej. `google/gemini-flash-latest`, `anthropic/claude-sonnet-4-6`, `bu-2-0`. |
| `BU_MAX_STEPS` | no | `25` | Pasos máximos por tarea si la petición no indica otro. |
| `BU_MAX_CONCURRENT_RUNS` | no | `1` | Tareas simultáneas. Con 1 GB de RAM deja en 1. |
| `BU_API_TOKEN` | no | — | Si lo defines, la API/UI exigen header `X-API-Token` (o `?token=`). Recomendado si expones la URL. |
| `BU_RUN_TTL_MINUTES` | no | `720` | Minutos que se guardan los resultados en memoria. |
| `PORT` | automática | — | La inyecta Railway. No tocar. |

\* El servicio arranca sin ninguna key (el healthcheck pasa), pero toda tarea devolverá error 400 con instrucciones hasta que añadas una.

## Uso: UI, API y ejemplos

### Web UI
Escribe la tarea en lenguaje natural, pulsa **Run agent** y espera. Al terminar verás resultado final, páginas visitadas y errores si los hubo.

### API REST

Lanzar tarea:

```bash
curl -X POST https://TU-SERVICIO.up.railway.app/api/runs \
  -H "Content-Type: application/json" \
  -H "X-API-Token: TU_TOKEN" \
  -d '{"task": "Busca vuelos Madrid-Lima en mayo y devuelve los 3 más baratos", "max_steps": 30}'
```

Respuesta `202`:

```json
{ "id": "a1b2c3d4e5f6", "status": "queued", "...": "..." }
```

Consultar resultado (polling):

```bash
curl -H "X-API-Token: TU_TOKEN" https://TU-SERVICIO.up.railway.app/api/runs/a1b2c3d4e5f6
```

Estados: `queued` → `running` → `finished` | `failed`.

Listar tareas: `GET /api/runs`. Documentación interactiva: `/docs`.

### Ejemplo Python

```python
import requests, time

BASE = "https://TU-SERVICIO.up.railway.app"
HEADERS = {"X-API-Token": "TU_TOKEN"}

r = requests.post(f"{BASE}/api/runs", headers={**HEADERS, "Content-Type": "application/json"},
                  json={"task": "Lee el último post del blog de railway.com y resume en 2 frases"})
rid = r.json()["id"]

while True:
    data = requests.get(f"{BASE}/api/runs/{rid}", headers=HEADERS).json()
    if data["status"] in ("finished", "failed"):
        print(data["result"] or data["error"])
        break
    time.sleep(5)
```

## Coste estimado

Railway cobra por uso real (RAM ~$10/GiB·mes, vCPU ~$20/vCPU·mes, volumen ~$0.15/GB·mes, prorrateados al segundo):

| Escenario | Consumo típico | Coste/mes aprox. |
| --- | --- | --- |
| Servicio idle (sin tareas) | ~150–250 MB RAM, CPU mínima | $1.5 – $3 |
| Uso ligero (unas decenas de tareas cortas) | picos de 700 MB–1 GB durante las tareas | $3 – $8 |
| Uso intensivo / varias tareas en paralelo | >1 GB sostenido | $10+ |

Con uso ligero cabe dentro del crédito incluido del plan Hobby ($5/mes). Recomendaciones para mantener el coste bajo:

- Memoria del servicio: **1024 MB** es suficiente para 1 tarea concurrente (512 MB puede quedarse corto con páginas pesadas).
- Mantén `BU_MAX_CONCURRENT_RUNS=1`.
- Usa Gemini free tier → coste LLM $0.
- El servicio consume RAM solo durante las tareas; entre tareas vuelve a idle barato.

## Persistencia

Todo estado importante vive en el volumen `/data`:

- `/data/profile` — perfil Chromium (cookies, sesiones, logins). Si haces login en un sitio, sobrevive reinicios y despliegues.
- `/data/downloads` — archivos que el agente descargue.

Los resultados de tareas se guardan solo en memoria (se pierden al redeploy). Si necesitas histórico permanente, consume la API desde tu app y guárdalo tú. Nota: no escales a más de 1 réplica mientras uses el perfil compartido.

## Seguridad

Por defecto la URL pública queda abierta: cualquiera con la URL podría gastar tus créditos LLM. Para producción:

1. Añade variable `BU_API_TOKEN` con un valor aleatorio largo (Railway → Variables → New → Generated Value funciona perfecto).
2. Redespliega. La UI pedirá el token una vez y lo recordará en tu navegador.
3. Todas las llamadas API deberán incluir el header `X-API-Token`.

## Troubleshooting

| Problema | Causa probable | Solución |
| --- | --- | --- |
| Tarea falla con `No LLM API key configured` | Falta la variable de la key | Añade `GOOGLE_API_KEY` (u otra) en Variables y espera el redeploy. |
| Error 401 en API/UI | Activaste `BU_API_TOKEN` | Envía header `X-API-Token` o pégalo cuando la UI lo pida. |
| El contenedor se reinicia durante tareas largas | OOM (sin RAM suficiente) | Sube memoria a 2048 MB o baja `BU_MAX_CONCURRENT_RUNS` a 1; reduce `max_steps` o usa un viewport/páginas más ligeras. |
| `chromium crashed` en logs | Poco shm o memoria | Ya se aplican flags de Docker automáticamente (`IN_DOCKER=true`). Si persiste, sube memoria. |
| La tarea termina pero `success=false` | El agente no consiguió el objetivo en N pasos | Sube `max_steps`, formula la tarea más concreta, o prueba un modelo mejor (Claude/GPT suelen seguir páginas complejas mejor que modelos mini). |
| Login hecho desaparece tras redeploy | Volumen no montado | Verifica que existe el volumen montado en `/data`. |
| Build tarda mucho la primera vez | Instala Chromium vía apt | Normal (3–6 min). Los siguientes builds usan caché. |

Logs del servicio: Railway → tu servicio → pestaña **Logs** (busca líneas `run <id> finished` o errores de Chromium).

## Licencias y créditos

- [browser-use](https://github.com/browser-use/browser-use) — MIT © Magnus Müller, Gregor Žunič y contribuidores.
- Este wrapper (API/UI/Dockerfile): MIT. Sin afiliación oficial con browser-use.

Enlaces útiles: [docs oficiales OSS](https://docs.browser-use.com/open-source/introduction) · [modelos soportados](https://docs.browser-use.com/open-source/supported-models) · [Discord browser-use](https://link.browser-use.com/discord)
