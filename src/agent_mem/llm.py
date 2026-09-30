"""Selected-provider chat completions shared by watch, migration and enrichment."""
from __future__ import annotations

from .config import get_llm_api_key, get_llm_model, get_llm_provider
from .engineering_store import redact


def complete_chat(messages: list[dict], *, temperature: float = 0.1) -> str:
    provider = get_llm_provider()
    label = 'Cerebras' if provider == 'cerebras' else 'Groq'
    key = get_llm_api_key(provider)
    model = get_llm_model(provider)
    command = f'agent-mem configure-{provider}'
    variable = f'{provider.upper()}_API_KEY'
    if not key:
        raise RuntimeError(f'{label} API key is not configured. Set {variable} or run {command}.')
    if not model:
        raise RuntimeError(f'{label} model is not configured. Run {command} --model <model-id>.')
    try:
        if provider == 'cerebras':
            from cerebras.cloud.sdk import Cerebras
            client = Cerebras(api_key=key, timeout=30, max_retries=1)
        else:
            from groq import Groq
            client = Groq(api_key=key)
    except ImportError as exc:
        package = 'cerebras-cloud-sdk' if provider == 'cerebras' else 'groq'
        raise RuntimeError(f'{label} client is not installed. Install {package}.') from exc
    try:
        with client:
            response = client.chat.completions.create(model=model, messages=messages, temperature=temperature)
        text = (response.choices[0].message.content or '').strip()
        if not text:
            raise RuntimeError(f'{label} returned no completion text.')
        return text
    except Exception as exc:
        message = str(redact(str(exc)))
        status = getattr(exc, 'status_code', None)
        lowered = message.lower()
        if status == 401 or 'invalid api key' in lowered or 'expired_api_key' in lowered:
            raise RuntimeError(f'{label} authentication failed. Check {variable} or run {command} with a valid key.') from exc
        if status == 404 or 'model_archived' in lowered:
            raise RuntimeError(f'{label} model {model!r} is unavailable or archived. Select an available model with {command} --model <model-id>.') from exc
        if status == 402:
            raise RuntimeError(f'{label} billing access is required. Enable billing or quota in the provider account, then retry the selected model.') from exc
        if status == 429:
            raise RuntimeError(f'{label} rate limit reached. Retry after the provider limit resets.') from exc
        if any(term in lowered for term in ('connection error', 'connecterror', 'timed out')):
            raise RuntimeError(f'{label} request failed due to a network problem. Retry when network access is available.') from exc
        raise RuntimeError(f'{label} request failed: {message}') from exc
