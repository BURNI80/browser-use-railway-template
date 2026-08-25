# Deploy and Host Browser Use on Railway

[Browser Use](https://github.com/browser-use/browser-use) is an open-source Python framework that lets AI agents control a real web browser: it reads pages, clicks, types, navigates, and extracts data like a human would. This template self-hosts it as a ready-to-use REST API + web dashboard running headless Chromium, so your agents can automate any website from a single HTTP call.

## About Hosting Browser Use

This template deploys one Docker service that packages the official `browser-use` library (v0.13.x) behind a lightweight FastAPI server. The container ships with headless Chromium and all required fonts pre-installed, so no browser setup is needed. Each submitted task runs asynchronously in its own browser session; results are queryable via REST or watched live from the built-in dashboard at `/`. A persistent Railway volume stores agent configuration and downloaded files across redeploys. The only thing you must provide is one LLM API key (Google Gemini's free tier works), set as an environment variable right after deploying.

## Common Use Cases

- **AI web scraping & data extraction** — point an agent at any site and get structured JSON back (prices, listings, contact info) without writing selectors.
- **Workflow automation (RPA)** — automate logins, form filling, downloads, and multi-step flows that break classic scrapers due to JavaScript or bot protection.
- **Automated end-to-end website testing** — describe expected behavior in natural language and let the agent verify it on every deploy.
- **Building AI assistants with web access** — give chatbots/agents the ability to browse, search, and act on the live web via a simple REST API.

## Dependencies for Browser Use Hosting

Browser Use needs a headless browser and an LLM to drive it. This template bundles everything except the LLM key:

### Deployment Dependencies

- **LLM API key** (required): set `GOOGLE_API_KEY` ([free tier available](https://aistudio.google.com/apikey)) right after deploying — or `BROWSER_USE_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` if you prefer another provider.
- **Railway Volume** (pre-configured by this template): 500MB persistent storage mounted at `/data` for agent configuration and downloaded files.
- **Headless Chromium + fonts**: already baked into the Docker image (Python 3.12 slim + Debian Chromium), nothing to install.

### Environment Variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GOOGLE_API_KEY` | Yes* | — | Google Gemini key. Free tier available. |
| `BROWSER_USE_API_KEY` | No | — | Browser Use cloud models (`bu-*`). |
| `OPENAI_API_KEY` | No | — | OpenAI models (`gpt-*`). |
| `ANTHROPIC_API_KEY` | No | — | Anthropic models (`claude-*`). |
| `BU_DEFAULT_MODEL` | No | `(auto)` | Default model, e.g. `google/gemini-2.5-flash`. |
| `BU_API_TOKEN` | No | — | If set, all requests need header `X-API-Token`. Recommended for public deployments. |
| `BU_MAX_CONCURRENT_RUNS` | No | `1` | Parallel browser sessions. Keep low on small plans (~1GB RAM each). |
| `BU_TASK_TIMEOUT_SECONDS` | No | `900` | Max duration of a single agent task. |
| `BU_MAX_STEPS` | No | `25` | Max agent steps per task. |
| `BU_HEADLESS` | No | `true` | Run Chromium headless (keep true on Railway). |

\* At least one provider key is needed to run tasks. Without one, the service still boots and `/health` stays green — tasks return a helpful error until you add a key.

## Using Your Deployment

Open the deployed URL for the dashboard, or use the REST API directly (interactive docs at `/docs`):

```bash
# Start a task
curl -X POST https://YOUR-APP.up.railway.app/api/runs \
  -H "Content-Type: application/json" \
  -d '{"task": "Go to news.ycombinator.com and list the top 3 titles"}'
# -> {"id": "...", "status": "running", ...}

# Poll for results
curl https://YOUR-APP.up.railway.app/api/runs/<id>
```

## Why Deploy Browser Use on Railway?

<!-- Recommended: Keep this section as shown below -->
Railway is a singular platform to deploy your infrastructure stack. Railway will host your infrastructure so you don't have to deal with configuration, while allowing you to vertically and horizontally scale it.

By deploying Browser Use on Railway, you are one step closer to supporting a complete full-stack application with minimal burden. Host your servers, databases, AI agents, and more on Railway.
<!-- End recommended section -->
