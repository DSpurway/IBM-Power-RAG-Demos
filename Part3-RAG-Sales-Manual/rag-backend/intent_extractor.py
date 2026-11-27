"""
Intent extraction: which IBM Power server is the question about, what kind of question
is it, and (for lifecycle questions) which date is wanted.

This replaces the watsonx Assistant that used to do this job. It works in two steps:

1. Deterministic: exact server model / MTM tokens from sources.json ("S924", "S924-G",
   "9009-42A"). Fast and exact, and it never invents a server.
2. LLM (optional): an OpenAI-compatible chat endpoint (the shared Granite on Spyre) reads
   the free-text question and returns JSON. Everything it returns is validated against
   sources.json, so it can only pick a server that really exists.

The LLM is enabled by setting LLM_BASE_URL (e.g. http://10.89.0.72:8000). Without it,
only step 1 runs. Any LLM failure falls back to step 1.
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

import requests

from server_mtm_mapper import MTM_SERVER_MAP, SERVER_MTM_MAP

logger = logging.getLogger(__name__)

LLM_BASE_URL = os.environ.get('LLM_BASE_URL', '').rstrip('/')
LLM_MODEL = os.environ.get('LLM_MODEL', 'ibm-granite/granite-4.1-8b-fp8')
LLM_API_KEY = os.environ.get('LLM_API_KEY', '')  # optional; the Spyre service needs none
INTENT_LLM_TIMEOUT = float(os.environ.get('INTENT_LLM_TIMEOUT', '20'))

QUERY_TYPES = ('table_lookup', 'activation_lookup', 'rag')
LIFECYCLE_FIELDS = ('announced', 'available', 'withdrawn', 'end_of_support',
                    'support_level_changed', 'discontinued')

_MTM_RE = re.compile(r'(?<![A-Z0-9])(\d{4}-[A-Z0-9]{3})(?![A-Z0-9])', re.IGNORECASE)


def _model_pattern(model: str) -> re.Pattern:
    """'S924-G' also matches 'S924G' and 'S924 G'; the token may not be inside a longer one."""
    escaped = re.escape(model).replace(r'\-', r'[-\s]?')
    return re.compile(rf'(?<![A-Z0-9]){escaped}(?![A-Z0-9])', re.IGNORECASE)


def find_servers(query: str) -> List[Tuple[str, Optional[str]]]:
    """
    Find server models named in a question.

    Returns a list of (model, mtm) without duplicates, in order of appearance. `mtm` is set
    only when the user wrote the MTM itself (it matters for S1112, which has two MTMs).
    """
    found: List[Tuple[int, str, Optional[str]]] = []
    text = query

    # MTMs first ("9009-42A"), then mask them so they cannot be matched again.
    for m in _MTM_RE.finditer(text):
        mtm = m.group(1).upper()
        model = MTM_SERVER_MAP.get(mtm)
        if model:
            found.append((m.start(), model, mtm))
            text = text[:m.start()] + ' ' * (m.end() - m.start()) + text[m.end():]

    # Models, longest first so "S924-G" is taken before "S924"; mask each match.
    for model in sorted(SERVER_MTM_MAP, key=len, reverse=True):
        pattern = _model_pattern(model)
        for m in pattern.finditer(text):
            found.append((m.start(), model, None))
            text = text[:m.start()] + ' ' * (m.end() - m.start()) + text[m.end():]

    result: List[Tuple[str, Optional[str]]] = []
    seen = set()
    for _, model, mtm in sorted(found):
        if (model, mtm) not in seen:
            seen.add((model, mtm))
            result.append((model, mtm))
    return result


def variant_options(model: str) -> List[Dict[str, str]]:
    """
    Choices to offer when a question names a model that has -G siblings ("S924" also
    exists as "S924-G", with a different MTM and a different sales manual).
    Returns [] when the model has no variants.
    """
    if '-' in model:  # already a specific variant, e.g. "S924-G"
        return []
    models = [m for m in SERVER_MTM_MAP if m == model or m.startswith(model + '-')]
    if len(models) < 2:
        return []
    return [{'label': f'IBM Power {m} ({SERVER_MTM_MAP[m]})', 'mtm': SERVER_MTM_MAP[m]}
            for m in sorted(models, key=lambda m: (len(m), m))]


def _server_list_for_prompt() -> str:
    by_model: Dict[str, List[str]] = {}
    for mtm, model in MTM_SERVER_MAP.items():
        by_model.setdefault(model, []).append(mtm)
    return '; '.join(f"{model} ({', '.join(sorted(mtms))})" for model, mtms in sorted(by_model.items()))


def _build_messages(query: str) -> List[Dict[str, str]]:
    system = (
        "You read questions about IBM Power servers and return ONE JSON object, nothing else.\n"
        "Fields:\n"
        '- "server_model": exactly one model from this list, or null if the question does not '
        "identify one server (a bare number such as 922 is ambiguous). Users write things like "
        '"the S924", "Power E980", "IBM Power System S922" or an MTM such as 9009-42A. '
        f"Models (MTMs): {_server_list_for_prompt()}.\n"
        '- "candidates": list of models from the list that the question could mean, when '
        "server_model is null; otherwise [].\n"
        '- "query_type": "table_lookup" for lifecycle dates; "activation_lookup" ONLY when the '
        'question asks about processor or memory ACTIVATION features (the word activation/activate '
        'or Capacity on Demand); "rag" for anything else, including memory size, maximum memory, '
        'cores, dimensions, weight, power, operating systems and other specifications.\n'
        '- "lifecycle_field": only for table_lookup, one of: "announced", "available", '
        '"withdrawn" (withdrawn from marketing, stop selling), "end_of_support" (stop supporting, '
        'end of support or service), "support_level_changed", "discontinued"; null if the '
        "question does not say which date.\n\n"
        'Example: "When did we stop supporting the S924?" -> '
        '{"server_model": "S924", "candidates": [], "query_type": "table_lookup", '
        '"lifecycle_field": "end_of_support"}\n'
        'Example: "What is the maximum memory of the E980?" -> '
        '{"server_model": "E980", "candidates": [], "query_type": "rag", '
        '"lifecycle_field": null}'
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": query}]


def _parse_json(text: str) -> Optional[dict]:
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _normalise_model(value) -> Optional[str]:
    """Return a model that exists in sources.json, or None."""
    if not isinstance(value, str):
        return None
    value = value.strip().upper()
    if value in SERVER_MTM_MAP:
        return value
    if value in MTM_SERVER_MAP:
        return MTM_SERVER_MAP[value]
    found = find_servers(value)
    return found[0][0] if len(found) == 1 else None


def validate_llm_result(data: dict) -> Dict[str, object]:
    """Keep only values that exist in sources.json / the allowed lists."""
    candidates = []
    for c in data.get('candidates') or []:
        model = _normalise_model(c)
        if model and model not in candidates:
            candidates.append(model)
    query_type = data.get('query_type')
    field = data.get('lifecycle_field')
    return {
        'server_model': _normalise_model(data.get('server_model')),
        'candidates': candidates,
        'query_type': query_type if query_type in QUERY_TYPES else None,
        'lifecycle_field': field if field in LIFECYCLE_FIELDS else None,
    }


def llm_extract(query: str) -> Optional[Dict[str, object]]:
    """Ask the LLM for server / query type / lifecycle field. None if unavailable or unusable."""
    if not LLM_BASE_URL:
        return None
    headers = {'Authorization': f'Bearer {LLM_API_KEY}'} if LLM_API_KEY else {}
    payload = {
        'model': LLM_MODEL,
        'messages': _build_messages(query),
        'temperature': 0,
        'max_tokens': 150,
    }
    try:
        resp = requests.post(f'{LLM_BASE_URL}/v1/chat/completions', json=payload,
                             headers=headers, timeout=INTENT_LLM_TIMEOUT)
        resp.raise_for_status()
        content = resp.json()['choices'][0]['message']['content']
    except (requests.RequestException, KeyError, IndexError, ValueError) as e:
        logger.warning(f"Intent LLM call failed, using deterministic result: {e}")
        return None
    data = _parse_json(content)
    if data is None:
        logger.warning(f"Intent LLM returned no JSON: {content[:200]!r}")
        return None
    result = validate_llm_result(data)
    logger.info(f"Intent LLM result: {result}")
    return result
