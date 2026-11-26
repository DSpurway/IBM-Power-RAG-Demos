"""
Section-aware chunker for IBM Power Sales Manual pages (v2), working from the clean tree in ibm_docs_tree.py.

Plan:
  Product life cycle dates   one chunk, Markdown table, direct lookup (no LLM)
  Abstract                   paragraph-split under the size cap (incl. "Model abstract")
  Highlights                 one chunk (splits only if over the cap)
  Description                split at its bold sub-headings (Summary of features, Memory, RAS ...), then by size
  Models                     SKIPPED, except the short "Model summary matrix"
  Technical description      one chunk per sub-heading (Physical specs, Operating environment, Hardware/Software
                             requirements ...), split by size only when over the cap
  Publications               low priority, split by size
  Features                   only "Feature descriptions": one chunk per feature (#XXXX), split only when over the cap.
                             "Features - No charge/Chargeable", "Feature availability matrix", "Feature exchanges" SKIPPED
  Accessories/Supplies/Trademarks and other small admin sections   SKIPPED
"""
import hashlib
import re
from datetime import datetime
from typing import Dict, Any, List, Tuple

from ibm_docs_tree import walk

VERSION = "2.0.0"
MAX_CHARS = 1500

SKIP_TOP = {"accessories", "supplies", "trademarks"}
SKIP_TITLES = {  # sub-sections judged unhelpful for Q&A
    "section 508 of the us rehabilitation act", "customer setup (csu)", "devices supported", "model conversions",
    "feature conversions", "features - no charge", "features - chargeable", "feature availability matrix",
    "feature exchanges", "customer replacement parts", "supplemental media", "terms of use",
}
PRIORITY = {
    "abstract": "high", "highlights": "medium", "description": "medium",
    "technical description": "high", "publications": "low", "models": "low"
}


def parse_feature_metadata(details: str) -> Dict[str, Any]:
    """Parse structured metadata from feature details text."""
    metadata = {}
    
    # Withdrawal date
    withdrawal_match = re.search(r'[Nn]o longer available as of ([A-Za-z]+ \d+,?\s*\d{4})', details)
    if withdrawal_match:
        metadata['withdrawal_date'] = withdrawal_match.group(1)
        metadata['is_withdrawn'] = True
    else:
        metadata['is_withdrawn'] = False
    
    # CSU (Customer Setup)
    csu_match = re.search(r'CSU:\s*(Yes|No)', details, re.IGNORECASE)
    if csu_match:
        metadata['csu'] = csu_match.group(1).lower() == 'yes'
    
    # Minimum/Maximum values (overall or first model)
    min_match = re.search(r'Minimum required:\s*(\d+)', details)
    if min_match:
        metadata['minimum_required'] = int(min_match.group(1))
    
    max_match = re.search(r'Maximum allowed:\s*(\d+)', details)
    if max_match:
        metadata['maximum_allowed'] = int(max_match.group(1))
    
    return metadata


# ---------------------------------------------------------------- size-capped splitting
def _segments(line: str, cap: int) -> list:
    if len(line) <= cap:
        return [line]
    out, cur = [], ""
    for sent in re.split(r"(?<=[.!?])\s+", line):
        for piece in ([sent] if len(sent) <= cap else _wordwrap(sent, cap)):
            if cur and len(cur) + 1 + len(piece) > cap:
                out.append(cur)
                cur = piece
            else:
                cur = f"{cur} {piece}" if cur else piece
    if cur:
        out.append(cur)
    return out


def _wordwrap(s: str, cap: int) -> list:
    out, cur = [], ""
    for w in s.split(" "):
        if cur and len(cur) + 1 + len(w) > cap:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}" if cur else w
    if cur:
        out.append(cur)
    return out


def _fit(block: str, cap: int) -> list:
    if len(block) <= cap:
        return [block]
    lines = block.split("\n")
    if lines[0].startswith("|") and len(lines) > 2:  # Markdown table: split by rows, repeat the header
        head, pieces, cur = lines[:2], [], lines[:2]
        for r in lines[2:]:
            if len(cur) > 2 and len("\n".join(cur + [r])) > cap:
                pieces.append("\n".join(cur))
                cur = list(head)
            cur.append(r)
        pieces.append("\n".join(cur))
        return pieces
    pieces, cur = [], ""
    for ln in lines:
        for seg in _segments(ln, cap):
            if cur and len(cur) + 1 + len(seg) > cap:
                pieces.append(cur)
                cur = seg
            else:
                cur = f"{cur}\n{seg}" if cur else seg
    if cur:
        pieces.append(cur)
    return pieces


def split_text(text: str, cap: int = MAX_CHARS) -> list:
    out, cur = [], ""
    for block in (b for b in text.split("\n\n") if b.strip()):
        for p in _fit(block.strip(), cap):
            if cur and len(cur) + 2 + len(p) > cap:
                out.append(cur)
                cur = ""
            cur = f"{cur}\n\n{p}" if cur else p
    if cur.strip():
        out.append(cur)
    return out


_MONTHS = {
    m: i for i, m in enumerate(
        ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
         "november", "december"], 1
    )
}
_DATE = re.compile(r"\b(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+(\d{4})\b", re.IGNORECASE)


def _iso_dates(text: str) -> str:
    return _DATE.sub(lambda m: f"{m.group(3)}-{_MONTHS[m.group(2).lower()]:02d}-{int(m.group(1)):02d}", text)


_BOLD = re.compile(r"^\*\*(.+)\*\*$")


def sub_blocks(text: str) -> list:
    """Split a section body at bold-only paragraphs -> [(sub_heading or None, body)]."""
    res, head, buf = [], None, []
    for b in text.split("\n\n"):
        m = _BOLD.match(b.strip())
        if m:
            if "".join(buf).strip():
                res.append((head, "\n\n".join(buf)))
            head, buf = m.group(1).strip(), []
        else:
            buf.append(b)
    if "".join(buf).strip():
        res.append((head, "\n\n".join(buf)))
    return res


# ---------------------------------------------------------------- chunking
def chunk_page(page: dict) -> Tuple[List[Dict[str, Any]], List[Tuple[str, int, str]]]:
    """Returns (chunks, skipped) where skipped = [(path, chars, reason)]."""
    mtm = page.get("mtm") or "unknown"
    name = page.get("page_title", "Untitled")
    url = page.get("url", "unknown")
    alltext = "".join(n["text"] for _, n in walk(page["tree"]))
    content_hash = hashlib.sha256(alltext.encode("utf-8")).hexdigest()
    common = {
        "content_hash": content_hash,
        "content_length": len(alltext),
        "ingestion_timestamp": datetime.utcnow().isoformat() + "Z",
        "chunker_version": VERSION,
        "published": page.get("published"),
    }
    chunks, skipped = [], []

    def base(section_type, title, path, priority, qtype, strategy, **extra):
        return {
            "section_type": section_type,
            "section_title": title,
            "section_path": " > ".join(path),
            "server_name": name,
            "mtm": mtm,
            "mtms": page.get("mtms", []),
            "family": page.get("family"),
            "source": url,
            "priority": priority,
            "query_type": qtype,
            "chunk_strategy": strategy,
            **extra,
            **common
        }

    def size(n):
        return len(n["text"]) + sum(size(c) for c in n["children"])

    def emit(node, path):
        top = path[0].lower()
        t = node["title"].lower()
        if t in SKIP_TITLES or (top in SKIP_TOP):
            skipped.append((" > ".join(path), size(node), "not useful for Q&A (plan)"))
            return
        if t == "feature descriptions":
            for f in node["children"]:
                m = re.match(r"\(#([A-Z0-9]{4})\)\s*-?\s*(.*)", f["title"])
                if not m or m.group(2).strip().startswith("-") or not f["text"]:
                    continue
                code, fname = m.group(1), m.group(2).strip()
                meta = parse_feature_metadata(f["text"])
                parts = split_text(f["text"])
                for i, part in enumerate(parts):
                    chunks.append({
                        "text": f"(#{code}) {fname}\n\n{part}",
                        "metadata": base(
                            "feature_code", "Feature descriptions", path, "high", "metadata_search",
                            "structured_section" if len(parts) == 1 else "structured_section_split",
                            feature_code=code, feature_name=fname, part_index=i, total_parts=len(parts), **meta
                        )
                    })
            return
        if top == "product life cycle dates":
            chunks.append({
                "text": "Product life cycle dates\n" + _iso_dates(node["text"]),
                "metadata": base(
                    "lifecycle_table", "Product lifecycle dates", path, "critical", "direct_lookup",
                    "preserve_table_structure"
                )
            })
            return
        # Models: keep only the short summary matrix
        if top == "models" and t not in ("models", "model summary matrix"):
            skipped.append((" > ".join(path), size(node), "Models detail skipped (plan)"))
            return
        for head, body in sub_blocks(node["text"]):
            p = path + ((head,) if head else ())
            parts = split_text(body)
            for i, part in enumerate(parts):
                chunks.append({
                    "text": f"{' > '.join(p)}\n\n{part}",
                    "metadata": base(
                        "content_section", p[-1], p, PRIORITY.get(top, "low"), "full_rag",
                        "keep_intact" if len(parts) == 1 else "section_split", part_index=i, total_parts=len(parts)
                    )
                })
        for c in node["children"]:
            emit(c, path + (c["title"],))

    for top in page["tree"]:
        emit(top, (top["title"],))
    return chunks, skipped
