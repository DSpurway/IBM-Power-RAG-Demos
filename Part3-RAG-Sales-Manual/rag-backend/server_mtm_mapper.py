"""
Server Model to MTM Mapper
Maps server models (e.g., "S924") to their MTMs (e.g., "9009-42A")
and generates collection names for OpenSearch
"""

import logging

logger = logging.getLogger(__name__)

# Complete mapping of server models to MTMs
SERVER_MTM_MAP = {
    # POWER11
    "E1180": "9080-HEU",
    "E1150": "9043-MRU",
    "S1124": "9824-42A",
    "S1122": "9824-22A",
    # POWER10
    "E1080": "9080-HEX",
    "E1050": "9043-MRX",
    "S1024": "9105-42A",
    "S1022": "9105-22A",
    "S1014": "9105-41B",
    "S1012": "9028-21B",
    "L1024": "9786-42H",
    "L1022": "9786-22H",
    # POWER9
    "E980": "9080-M9S",
    "E950": "9040-MR9",
    "S924": "9009-42A",
    "S924-G": "9009-42G",
    "S922": "9009-22A",
    "S922-G": "9009-22G",
    "S914": "9009-41A",
    "S914-G": "9009-41G",
    "H924": "9223-42S",
    "H922": "9223-22S",
    "IC922": "9183-22X",
    "L922": "9008-22L",
    "LC922": "9006-22P",
    "LC921": "9006-12P",
}

# Reverse mapping: MTM to server model
MTM_SERVER_MAP = {mtm: model for model, mtm in SERVER_MTM_MAP.items()}


def get_mtm_for_model(server_model: str) -> str:
    """
    Get MTM for a server model
    
    Args:
        server_model: Server model (e.g., "S924", "E1180")
        
    Returns:
        MTM string (e.g., "9009-42A") or None if not found
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


def get_collection_name_for_mtm(mtm: str) -> str:
    """
    Generate collection name for an MTM
    
    Args:
        mtm: MTM string (e.g., "9009-42A")
        
    Returns:
        Collection name (e.g., "mtm_9009_42a")
    """
    # Convert MTM to collection name format
    collection_name = f"mtm_{mtm.lower().replace('-', '_')}"
    logger.info(f"Generated collection name for MTM {mtm}: {collection_name}")
    return collection_name


def get_collection_name_for_model(server_model: str) -> str:
    """
    Get collection name for a server model
    
    Args:
        server_model: Server model (e.g., "S924")
        
    Returns:
        Collection name (e.g., "mtm_9009_42a") or None if model not found
    """
    mtm = get_mtm_for_model(server_model)
    if mtm:
        return get_collection_name_for_mtm(mtm)
    return None


# Made with Bob