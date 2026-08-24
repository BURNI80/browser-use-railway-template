# Texto listo para el formulario "Publish as Template"

## Nombre

Browser Use

## Descripción corta

Self-host the #1 open-source AI browser agent (79k stars): launch headless-Chromium tasks from a web UI or REST API with any LLM.

## Categoría

AI / Agents (o "Artificial Intelligence" según el selector)

## Icono

Logo 1:1 transparente de browser-use (media kit oficial) o globo terráqueo genérico si no se permite la marca.

## Overview (pegar tal cual)

# Deploy and Host Browser Use with Railway

Browser Use is the leading open-source library for AI browser automation (79k+ GitHub stars). This template runs it as a single self-hosted service: describe a task in natural language and an AI agent drives a real headless Chromium — navigating, clicking, filling forms, and extracting data — then returns the result through a built-in web UI or a clean REST API.

## About Hosting Browser Use

Hosting Browser Use means running one Python service that bundles the agent library and its own Chromium instance. You bring an LLM API key (Google Gemini works on its free tier), set it once as a variable, and the service handles task execution, session persistence on a volume, healthchecks, and automatic restarts. No database is required — results are served over HTTP and browser logins survive redeploys thanks to the persistent profile directory.

## Common Use Cases

- Automate repetitive web workflows: form filling, checkouts, data entry across internal portals
- Scheduled scraping and monitoring that needs logged-in sessions (cookies persist on the volume)
- Add a browser-using AI agent to your own product via the REST API (`POST /api/runs`)
- QA smoke-tests of real user flows without writing Playwright scripts
- Research assistants that read several sites and return structured summaries

## Dependencies for Browser Use Hosting

- An LLM provider key: Google Gemini (free tier available), OpenAI, Anthropic, or Browser Use Cloud models
- Chromium is installed inside the image from Debian packages — nothing external to configure
- Persistent volume for the browser profile (created automatically by the template)

### Deployment Dependencies

- https://github.com/browser-use/browser-use (upstream project, MIT)
- https://docs.browser-use.com/open-source/introduction
- https://aistudio.google.com/apikey (free Gemini key)

### Implementation Details

- Single service: FastAPI wrapper pinned to `browser-use==0.13.8`, exposing `/api/runs`, `/docs` (Swagger), `/health`
- Optional token auth via `BU_API_TOKEN` to protect your LLM credits when the URL is public
- Concurrency capped at 1 run by default so the default 1 GB memory fits the Hobby plan
- Healthcheck at `/health` keeps failed deploys from receiving traffic

## Why Deploy Browser Use on Railway?

Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying Browser Use on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
