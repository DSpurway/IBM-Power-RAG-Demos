"""
Server Model / MTM / Family mapper.

The list of servers comes from sources.json (generated from the scraped corpus by
laptop-scraper/make_sources.py), so there is one source of truth and no hand-written
server list to drift out of date.

    "S924"      -> MTM "9009-42A"            (get_mtm_for_model)
    "9009-42A"  -> family "9009-02"          (MTM_FAMILY_MAP)
    family      -> OpenSearch collection     (get_collection_name_for_family)

A family can hold several MTMs (e.g. S1112 = 9242-21B rack and 9242-21T tower); they
share one collection because they share one IBM Sales Manual page.
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# Get OpenSearch prefix from environment (same as app.py)
OPENSEARCH_DB_PREFIX = os.environ.get('OPENSEARCH_DB_PREFIX', 'rag').lower()

SOURCES_FILE = os.environ.get(
    'SOURCES_FILE',
    os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sources.json'),
)

# "IBM Power System S924-G" / "IBM Power S1022" -> "S924-G" / "S1022"
_NAME_PREFIX = re.compile(r'^IBM\s+Power(\s+Systems?)?\s+', re.IGNORECASE)


def _model_from_name(name: str) -> str:
    return _NAME_PREFIX.sub('', name).strip().upper()


def _load_sources():
    """Return (SERVER_MTM_MAP, MTM_SERVER_MAP, MTM_FAMILY_MAP) built from sources.json."""
    server_mtm, mtm_server, mtm_family = {}, {}, {}
    try:
        with open(SOURCES_FILE, encoding='utf-8') as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        logger.error(f"Cannot load {SOURCES_FILE}: {e}. Server/MTM lookups will be empty.")
        return server_mtm, mtm_server, mtm_family

    for doc_set in data.get('sets', []):
        for source in doc_set.get('sources', []):
            model = _model_from_name(source['name'])
            mtms = source.get('mtms') or []
            if mtms:
                server_mtm[model] = mtms[0]
            for mtm in mtms:
                mtm_server[mtm.upper()] = model
                mtm_family[mtm.upper()] = source['family']
    return server_mtm, mtm_server, mtm_family


# model -> first MTM of its family; MTM -> model; MTM -> family
SERVER_MTM_MAP, MTM_SERVER_MAP, MTM_FAMILY_MAP = _load_sources()


def get_mtm_for_model(server_model: str) -> str:
    """
    Get MTM for a server model

    Args:
        server_model: Server model (e.g., "S924", "E1180")

    Returns:
        MTM string (e.g., "9009-42A") or None if not found. For a model with several
        MTMs (S1112) this is the first one; the others are in MTM_SERVER_MAP.
    """
    # Normalize model name (remove "IBM Power" prefix, etc.)
    model = server_model.upper().strip()
    model = model.replace("IBM", "").replace("POWER", "").replace("SYSTEM", "").strip()

    mtm = SERVER_MTM_MAP.get(model)
    if mtm:
        logger.info(f"Mapped model {server_model} -> {model} -> MTM {mtm}")
    else:
        logger.warning(f"No MTM mapping found for model: {server_model} (normalized: {model})")

    return mtm


def get_collection_name_for_family(family: str) -> str:
    """Collection name for a family (must match /api/ingest-chunks), e.g. "rag_family_9009_02"."""
    return f"{OPENSEARCH_DB_PREFIX}_family_{family.lower().replace('-', '_')}"


def get_collection_name_for_mtm(mtm: str) -> str:
    """
    Generate collection name for an MTM

    Args:
        mtm: MTM string (e.g., "9009-42A")

    Returns:
        Collection name of the MTM's family (e.g., "rag_family_9009_02"). An MTM that is
        not in sources.json falls back to the legacy per-MTM name ("rag_mtm_...").
    """
    family = MTM_FAMILY_MAP.get(mtm.upper())
    if family:
        collection_name = get_collection_name_for_family(family)
    else:
        collection_name = f"{OPENSEARCH_DB_PREFIX}_mtm_{mtm.lower().replace('-', '_')}"
        logger.warning(f"MTM {mtm} is not in sources.json; using legacy collection {collection_name}")
    logger.info(f"Generated collection name for MTM {mtm}: {collection_name}")
    return collection_name


def get_collection_name_for_model(server_model: str) -> str:
    """
    Get collection name for a server model

    Args:
        server_model: Server model (e.g., "S924")

    Returns:
        Collection name (e.g., "rag_family_9009_02") or None if model not found
    """
    mtm = get_mtm_for_model(server_model)
    if mtm:
        return get_collection_name_for_mtm(mtm)
    return None


# Made with Bob
