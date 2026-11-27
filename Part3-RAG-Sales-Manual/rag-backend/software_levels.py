"""Oldest AIX / IBM i level in the manual's "Software requirements" lists.

Each list is headed "If installing the AIX operating system LPAR (one of these):". A small LLM tends to
pick the first or newest line instead of the oldest, so for "minimum level" questions the answer is
worked out here and handed to the LLM as a fact.
"""
import re

MINIMUM_WORDS = re.compile(r"\b(?:minimum|minimal|oldest|earliest|lowest|at\s+least)\b", re.IGNORECASE)

# Groups: release, version, then Technology Level (AIX) or Technology Refresh (IBM i); missing = 0
_LEVEL = {
    'aix': re.compile(r"AIX\s+(?:Version\s+)?(\d+)\.(\d+)(?:\s+with\s+the\s+\d{4}-(\d{2})\s+Technology\s+Level)?",
                      re.IGNORECASE),
    'ibm i': re.compile(r"IBM\s+i\s+(\d+)\.(\d+)(?:\s+TR(\d+))?", re.IGNORECASE),
}
_LEAD_IN = re.compile(r"^If installing (?:the )?(?:operating system )?|\s*\(one of these\):?\s*$", re.IGNORECASE)


def oldest_levels(texts, terms):
    """["AIX LPAR with any I/O configuration: AIX Version 6.1 with the 6100-09 ...", ...] for AIX / IBM i in `terms`."""
    out = []
    for name in (t for t in terms if t in _LEVEL):
        rx = _LEVEL[name]
        for text in texts:
            lead, best = None, None  # lead-in of the current list; (key, line) of its oldest level
            for line in text.split('\n') + ['If installing (end)']:
                line = line.strip()
                if line.lower().startswith('if installing'):
                    if lead and best:
                        out.append(f"{lead}: {best[1]}")
                    lead, best = _LEAD_IN.sub('', line), None
                elif lead and line.startswith('-'):
                    item = line.lstrip('- ').strip()
                    m = rx.match(item)
                    if m:
                        key = tuple(int(g) if g else 0 for g in m.groups())
                        if best is None or key < best[0]:
                            best = (key, item)
    return out
