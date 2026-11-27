"""Oldest / supported AIX and IBM i levels in the manual's "Software requirements" lists.

Each list is headed "If installing the AIX operating system LPAR (one of these):". A small LLM tends to
pick the first or newest line instead of the oldest, so for "minimum level" and "what level is needed"
questions the answer is worked out here and handed to the LLM as a fact.
"""
import re

MINIMUM_WORDS = re.compile(r"\b(?:minimum|minimal|oldest|earliest|lowest|at\s+least)\b", re.IGNORECASE)

# Groups: release, version, then Technology Level (AIX) or Technology Refresh (IBM i); missing = 0
_LEVEL = {
    'aix': re.compile(r"AIX\s+(?:Version\s+)?(\d+)\.(\d+)(?:\s+with\s+the\s+\d{4}-(\d{2})\s+Technology\s+Level)?",
                      re.IGNORECASE),
    'ibm i': re.compile(r"IBM\s+i\s+(\d+)\.(\d+)(?:\s+TR(\d+))?", re.IGNORECASE),
}
_LEAD_IN = re.compile(r"^If installing (?:the )?(?:operating system )?|\s*(?:\(one of these\))?:?\s*$", re.IGNORECASE)


def _lists(texts, terms):
    """Yield (lead-in, [(level key, item), ...]) for each list of AIX / IBM i levels found in `texts`."""
    for name in (t for t in terms if t in _LEVEL):
        rx = _LEVEL[name]
        for text in texts:
            lead, items = None, []
            for line in text.split('\n') + ['If installing (end)']:
                line = line.strip()
                if line.lower().startswith('if installing'):
                    if lead and items:
                        yield lead, items
                    lead, items = _LEAD_IN.sub('', line), []
                elif lead and line.startswith('-'):
                    item = line.lstrip('- ').strip()
                    m = rx.match(item)
                    if m:
                        items.append((tuple(int(g) if g else 0 for g in m.groups()), item))


def oldest_levels(texts, terms):
    """["AIX LPAR with any I/O configuration: AIX Version 6.1 with the 6100-09 ...", ...] for AIX / IBM i in `terms`."""
    return [f"{lead}: {min(items, key=lambda i: i[0])[1]}" for lead, items in _lists(texts, terms)]


def supported_releases(texts, terms):
    """One line per list: its lowest listed level for each release, newest release first."""
    out = []
    for lead, items in _lists(texts, terms):
        lowest = {}
        for key, item in items:
            release = key[:2]
            if release not in lowest or key < lowest[release][0]:
                lowest[release] = (key, item)
        out.append(f"{lead}: " + "; ".join(lowest[r][1] for r in sorted(lowest, reverse=True)))
    return out
