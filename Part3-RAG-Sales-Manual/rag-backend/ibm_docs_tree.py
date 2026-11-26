"""
Parse a rendered IBM Docs Sales Manual page into a clean section tree.

The page is a set of nested <article class="topic nestedN"> elements (nested1 = H2 ... nested3 = H4), each with
a heading and a body. Text is rendered with block separators (the old scraper glued blocks together), tables
become Markdown, lists become "- " bullets, and bold-only paragraphs (<p><strong>X</strong></p>, used for the
sub-headings inside Description) are kept as "**X**" lines for the chunker to split on.

Node: {"level": 2..4, "title": str, "text": str, "children": [node]}
"""
import hashlib
import re
from bs4 import BeautifulSoup, NavigableString

from web_scraper import html_table_to_markdown

_WS = re.compile(r"[ \t\r\f\v]+")


def _clean(s: str) -> str:
    """Collapse all whitespace (IBM's HTML hard-wraps lines mid-sentence); \\x00 marks a real <br> line break.
    U+2011 (non-breaking hyphen, used in newer pages) is normalised so searches match plain-hyphen terms."""
    s = s.replace("\xa0", " ").replace("\u2011", "-").replace("\u200b", "")
    s = " ".join(s.split())
    return s.replace(" \x00 ", "\n").replace("\x00 ", "\n").replace(" \x00", "\n").replace("\x00", "\n").strip()


def _inline(el) -> str:
    for br in el.find_all("br"):
        br.replace_with("\x00")
    return _clean(el.get_text(""))


def _list(el, depth=0) -> str:
    lines = []
    for li in el.find_all("li", recursive=False):
        own, nested = [], []
        for c in li.children:
            if getattr(c, "name", None) in ("ul", "ol"):
                nested.append(c)
            elif isinstance(c, NavigableString):
                own.append(str(c))
            else:
                own.append(c.get_text(""))
        txt = _clean(" ".join(own))
        if txt:
            lines.append("  " * depth + "- " + txt)
        for n in nested:
            sub = _list(n, depth + 1)
            if sub:
                lines.append(sub)
    return "\n".join(lines)


def _blocks(el) -> list:
    out = []
    for c in el.children:
        if isinstance(c, NavigableString):
            s = _clean(str(c))
            if s:
                out.append(s)
            continue
        n = c.name
        if n == "table":
            out.append(html_table_to_markdown(c).strip())
        elif n in ("ul", "ol"):
            out.append(_list(c))
        elif n == "p":
            t = _inline(c)
            kids = [k for k in c.children if not (isinstance(k, NavigableString) and not str(k).strip())]
            if t and len(kids) == 1 and getattr(kids[0], "name", None) in ("strong", "b"):
                out.append(f"**{t}**")
            elif t:
                out.append(t)
        elif n in ("div", "section", "dl", "blockquote"):
            inner = "\n\n".join(b for b in _blocks(c) if b)
            if inner:
                cls = " ".join(c.get("class", []))
                out.append(("Note: " + inner) if "note" in cls.split() else inner)
        elif n in ("script", "style"):
            continue
        else:
            t = _inline(c)
            if t:
                out.append(t)
    return [b for b in out if b]


def _node(a) -> dict:
    cls = " ".join(a.get("class", []))
    m = re.search(r"nested(\d)", cls)
    level = int(m.group(1)) + 1 if m else 1
    h = a.find(re.compile(r"^h[1-6]$"), recursive=False)
    title = _clean(h.get_text("")) if h else ""
    body = []
    for c in a.children:
        if getattr(c, "name", None) in (None,) or re.match(r"^h[1-6]$", c.name or "") or c.name == "article":
            continue
        tmp = BeautifulSoup("<div></div>", "html.parser").div
        tmp.append(c.__copy__())
        body.extend(_blocks(tmp))
    kids = [_node(k) for k in a.find_all("article", class_="topic", recursive=False)]
    return {"level": level, "title": title, "text": "\n\n".join(body).strip(), "children": kids}


def parse_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one("div.ibmdocs-content-container")
    if root is None:
        raise ValueError("ibmdocs-content-container not found")
    h1 = root.find("h1")
    title = _clean(h1.get_text("")) if h1 else ""
    pub = re.search(r"Published:\s*([^\[\n]+)", root.get_text("\n"))
    mt = re.search(r"\((\d{4}-[A-Z0-9]{3})\)", title)
    tree = [_node(a) for a in root.select("article.topic.nested1")]
    # A page is a "family" and may cover several MTMs (e.g. 9242-21B and 9242-21T); the lifecycle table lists them.
    fam = re.search(r"Family\s+(\d{4}[+\-]\d{2})", title)
    fam_str = fam.group(1).replace("+", "-") if fam else None
    mach_type = fam_str.split("-")[0] if fam_str else (mt.group(1).split("-")[0] if mt else None)
    lc = next((n for n in tree if re.match(r"product life ?cycle dates", n["title"], re.I)), None)
    
    # If lifecycle table uses short model suffixes (e.g. '| MRU |' instead of '| 9043-MRU |') and machine type is known:
    if lc and mach_type:
        lc["text"] = re.sub(r'\|\s*([A-Z0-9]{3})\s*\|', rf'| {mach_type}-\1 |', lc["text"])
    
    mtms = list(dict.fromkeys(re.findall(r"\b\d{4}-[A-Z0-9]{3}\b", lc["text"]))) if lc else []
    if not mtms:
        if mt:
            mtms = [mt.group(1)]
        else:
            mtms = list(dict.fromkeys(re.findall(r"\b\d{4}-[A-Z0-9]{3}\b", root.get_text("\n"))))
            
    primary_mtm = mt.group(1) if mt else (mtms[0] if mtms else None)
    return {
        "page_title": title,
        "family": fam_str,
        "mtms": mtms,
        "mtm": primary_mtm,
        "published": pub.group(1).strip() if pub else None,
        "tree": tree,
        "html_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
    }


def walk(nodes, path=()):
    for n in nodes:
        p = path + (n["title"],)
        yield p, n
        yield from walk(n["children"], p)
