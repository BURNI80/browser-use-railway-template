"""Browser Use self-hosted server: REST API + web UI on top of the open-source browser-use library."""

import asyncio
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

os.environ.setdefault('IN_DOCKER', 'true')
os.environ.setdefault('ANONYMIZED_TELEMETRY', 'false')
os.environ.setdefault('BROWSER_USE_CLOUD_SYNC', 'false')
os.environ.setdefault('BROWSER_USE_VERSION_CHECK', 'false')

import browser_use
from browser_use import (
    Agent,
    BrowserProfile,
    BrowserSession,
    ChatAnthropic,
    ChatBrowserUse,
    ChatGoogle,
    ChatOpenAI,
)

logging.basicConfig(level=os.getenv('BU_LOG_LEVEL', 'INFO'))
logger = logging.getLogger('bu-server')

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / 'static'
DATA_DIR = Path(os.getenv('BU_DATA_DIR', '/data'))
PROFILE_DIR = DATA_DIR / 'profile'
DOWNLOADS_DIR = DATA_DIR / 'downloads'

API_TOKEN = os.getenv('BU_API_TOKEN', '').strip()
DEFAULT_MODEL = os.getenv('BU_DEFAULT_MODEL', '').strip()
DEFAULT_MAX_STEPS = int(os.getenv('BU_MAX_STEPS', '25'))
MAX_CONCURRENT_RUNS = max(1, int(os.getenv('BU_MAX_CONCURRENT_RUNS', '1')))
RUN_TTL_MINUTES = int(os.getenv('BU_RUN_TTL_MINUTES', '720'))

PROVIDERS = {
    'google': {'env': 'GOOGLE_API_KEY', 'cls': ChatGoogle, 'example': 'gemini-flash-latest', 'key_url': 'https://aistudio.google.com/apikey'},
    'browser-use': {'env': 'BROWSER_USE_API_KEY', 'cls': ChatBrowserUse, 'example': 'bu-2-0', 'key_url': 'https://cloud.browser-use.com/new-api-key'},
    'openai': {'env': 'OPENAI_API_KEY', 'cls': ChatOpenAI, 'example': 'gpt-4.1-mini', 'key_url': 'https://platform.openai.com/api-keys'},
    'anthropic': {'env': 'ANTHROPIC_API_KEY', 'cls': ChatAnthropic, 'example': 'claude-sonnet-4-6', 'key_url': 'https://console.anthropic.com/settings/keys'},
}
GUESS_RULES = (
    ('bu-', 'browser-use'),
    ('gpt-', 'openai'),
    ('o3-', 'openai'),
    ('o4-', 'openai'),
    ('claude-', 'anthropic'),
)

START_TIME = time.time()
app = FastAPI(title='Browser Use Server', version='1.0.0', docs_url='/docs', redoc_url=None)
_semaphore = asyncio.Semaphore(MAX_CONCURRENT_RUNS)
_runs: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def provider_status() -> dict[str, bool]:
    return {name: bool(os.getenv(cfg['env'], '').strip()) for name, cfg in PROVIDERS.items()}


def _call(obj, name, default=None):
    attr = getattr(obj, name, None)
    if attr is None:
        return default
    try:
        value = attr() if callable(attr) else attr
    except Exception:
        return default
    return default if value is None else value


def check_auth(x_api_token: str | None = Header(default=None), token: str | None = Query(default=None)):
    """Require BU_API_TOKEN when configured; accept header X-API-Token or ?token=."""
    if not API_TOKEN:
        return
    provided = (x_api_token or token or '').strip()
    if provided != API_TOKEN:
        raise HTTPException(status_code=401, detail='Invalid or missing API token (send header X-API-Token)')


class RunCreate(BaseModel):
    task: str = Field(min_length=1, max_length=10000)
    model: str | None = Field(default=None, max_length=200)
    max_steps: int | None = Field(default=None, ge=1, le=200)


def build_llm(model: str | None):
    raw = (model or DEFAULT_MODEL).strip()
    if not raw:
        for name in ('google', 'browser-use', 'openai', 'anthropic'):
            cfg = PROVIDERS[name]
            if os.getenv(cfg['env'], '').strip():
                raw = f'{name}/{cfg["example"]}'
                break
    if not raw:
        raise HTTPException(
            status_code=400,
            detail={
                'message': 'No LLM API key configured.',
                'hint': 'Add GOOGLE_API_KEY (free tier) or another provider key in Railway > your service > Variables.',
                'get_key': PROVIDERS['google']['key_url'],
            },
        )
    provider = None
    name = raw
    if '/' in raw:
        prefix, rest = raw.split('/', 1)
        if prefix in PROVIDERS:
            provider, name = prefix, rest
    if provider is None:
        low = raw.lower()
        provider = next((p for prefix, p in GUESS_RULES if low.startswith(prefix)), 'google')
    cfg = PROVIDERS[provider]
    if not os.getenv(cfg['env'], '').strip():
        raise HTTPException(
            status_code=400,
            detail={
                'message': f'Model "{raw}" needs the {provider} provider.',
                'hint': f'Set variable {cfg["env"]} in Railway > your service > Variables and redeploy.',
                'get_key': cfg['key_url'],
            },
        )
    llm = cfg['cls'](model=name)
    return provider, raw, llm


async def _close_session(session) -> None:
    for method_name in ('stop', 'close', 'kill'):
        method = getattr(session, method_name, None)
        if callable(method):
            try:
                result = method()
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.debug('session cleanup via %s raised', method_name, exc_info=True)
            return

async def _execute_run(run: dict) -> None:
    session = None
    try:
        _, model_str, llm = build_llm(run.get('model'))
        run['model'] = model_str
        run['status'] = 'running'
        run['started_at'] = _now_iso()
        profile = BrowserProfile(
            headless=True,
            user_data_dir=str(PROFILE_DIR),
            downloads_path=str(DOWNLOADS_DIR),
        )
        session = BrowserSession(browser_profile=profile)
        agent = Agent(task=run['task'], llm=llm, browser_session=session, max_steps=run['max_steps'])
        async with _semaphore:
            history = await agent.run()
        run['result'] = _call(history, 'final_result', '')
        run['success'] = bool(_call(history, 'is_successful', False))
        urls = _call(history, 'urls', [])
        run['urls'] = list(urls)[:50] if urls else []
        errors = _call(history, 'errors', [])
        run['errors'] = [str(e) for e in errors][:10] if errors else []
        steps = _call(history, 'history', [])
        run['steps'] = len(steps) if steps is not None else 0
        run['status'] = 'finished'
        logger.info('run %s finished ok=%s steps=%s', run['id'], run['success'], run['steps'])
    except HTTPException as exc:
        run['status'] = 'failed'
        run['error'] = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    except Exception as exc:
        logger.exception('run %s failed', run['id'])
        run['status'] = 'failed'
        run['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        if session is not None:
            await _close_session(session)
        run['finished_at'] = _now_iso()


async def _cleanup_loop() -> None:
    while True:
        await asyncio.sleep(600)
        cutoff = time.time() - RUN_TTL_MINUTES * 60
        stale = [
            rid
            for rid, v in _runs.items()
            if v['status'] in ('finished', 'failed')
            and (ts := _parse_ts(v.get('finished_at'))) is not None
            and ts < cutoff
        ]
        for rid in stale:
            _runs.pop(rid, None)


def _parse_ts(value):
    try:
        return datetime.fromisoformat(value).timestamp() if value else None
    except ValueError:
        return None


@app.on_event('startup')
async def startup() -> None:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.create_task(_cleanup_loop())
    logger.info(
        'browser_use=%s providers=%s auth=%s concurrency=%s',
        getattr(browser_use, '__version__', '?'),
        provider_status(),
        bool(API_TOKEN),
        MAX_CONCURRENT_RUNS,
    )


@app.get('/')
async def index():
    return FileResponse(STATIC_DIR / 'index.html')


@app.get('/health')
async def health():
    active = sum(1 for r in _runs.values() if r['status'] in ('queued', 'running'))
    return {
        'status': 'ok',
        'service': 'browser-use-server',
        'library_version': getattr(browser_use, '__version__', 'unknown'),
        'uptime_seconds': round(time.time() - START_TIME, 1),
        'auth_required': bool(API_TOKEN),
        'providers_configured': provider_status(),
        'default_model': DEFAULT_MODEL or '(auto)',
        'active_runs': active,
        'max_concurrent_runs': MAX_CONCURRENT_RUNS,
    }


@app.get('/api/providers')
async def providers():
    return {
        'default_model': DEFAULT_MODEL or None,
        'providers': [
            {
                'name': name,
                'configured': bool(os.getenv(cfg['env'], '').strip()),
                'env_var': cfg['env'],
                'example_model': cfg['example'],
                'get_key_url': cfg['key_url'],
            }
            for name, cfg in PROVIDERS.items()
        ],
    }


@app.post('/api/runs', status_code=202, dependencies=[Depends(check_auth)])
async def create_run(body: RunCreate):
    pending = sum(1 for r in _runs.values() if r['status'] in ('queued', 'running'))
    if pending >= MAX_CONCURRENT_RUNS * 10:
        raise HTTPException(status_code=429, detail='Too many runs. Wait for current runs to finish.')
    run_id = uuid.uuid4().hex[:12]
    run = {
        'id': run_id,
        'task': body.task.strip(),
        'model': body.model or None,
        'max_steps': body.max_steps or DEFAULT_MAX_STEPS,
        'status': 'queued',
        'created_at': _now_iso(),
        'started_at': None,
        'finished_at': None,
        'result': None,
        'error': None,
        'success': None,
        'steps': 0,
        'urls': [],
        'errors': [],
    }
    _runs[run_id] = run
    asyncio.create_task(_execute_run(run))
    logger.info('run %s queued model=%s steps=%s', run_id, run['model'], run['max_steps'])
    return run


@app.get('/api/runs', dependencies=[Depends(check_auth)])
async def list_runs():
    summary_keys = ('id', 'task', 'status', 'model', 'created_at', 'finished_at', 'success', 'steps')
    ordered = sorted(_runs.values(), key=lambda r: r['created_at'], reverse=True)
    return [{k: r[k] for k in summary_keys} for r in ordered]


@app.get('/api/runs/{run_id}', dependencies=[Depends(check_auth)])
async def get_run(run_id: str):
    run = _runs.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail='Run not found (results are kept in memory and expire after a while)')
    return run
