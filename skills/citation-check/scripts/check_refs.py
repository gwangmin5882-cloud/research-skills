#!/usr/bin/env python3
"""
check_refs.py - check that references really exist, using free public APIs
(Crossref, OpenAlex, arXiv, DataCite, doi.org). Standard library only.

Usage
  python check_refs.py refs.bib                 # BibTeX
  python check_refs.py refs.txt                 # one reference per line (or blank-line separated)
  python check_refs.py refs.json                # [{"key", "title", "authors": [...], "year", "doi"}]
  python check_refs.py refs.bib --abstracts     # also fetch abstracts (for claim checking)
  python check_refs.py refs.bib --out mydir --lang en

Outputs (in --out, default ./citation_check)
  citation_report.md     human-readable report
  citation_report.json   machine-readable results (abstracts included with --abstracts)

What is sent over the network: only each reference's title, authors, year and
DOI/arXiv ID. Manuscript text never leaves the machine.

Optional environment variables
  CROSSREF_MAILTO   your e-mail, added to requests for Crossref/OpenAlex "polite pool"
  OPENALEX_API_KEY  OpenAlex API key, if you have one
"""

import argparse
import datetime as _dt
import difflib
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

VERSION = "0.1.0"
MAILTO = os.environ.get("CROSSREF_MAILTO", "").strip()
OPENALEX_KEY = os.environ.get("OPENALEX_API_KEY", "").strip()
UA = f"research-skills-citation-check/{VERSION}" + (f" (mailto:{MAILTO})" if MAILTO else "")

# ---------------------------------------------------------------- labels

STATUS = {
    "VERIFIED": ("확인됨", "Verified"),
    "METADATA_MISMATCH": ("정보 일부 틀림", "Metadata mismatch"),
    "ID_MISMATCH": ("식별자 불일치", "Identifier points elsewhere"),
    "SIMILAR_ONLY": ("비슷한 논문만 있음", "Only a similar paper exists"),
    "NOT_FOUND": ("찾을 수 없음", "Not found"),
    "UNVERIFIABLE": ("확인 불가", "Unverifiable"),
    "PLACEHOLDER": ("자리표시 문구", "Placeholder text"),
    "ERROR": ("조회 오류", "Lookup error"),
}
SEVERITY = ["ID_MISMATCH", "NOT_FOUND", "PLACEHOLDER", "SIMILAR_ONLY",
            "METADATA_MISMATCH", "UNVERIFIABLE", "ERROR", "VERIFIED"]

MSG = {
    "ko": {
        "doi_ok": "DOI가 실제 논문으로 연결되고 제목이 일치합니다",
        "doi_only": "DOI는 존재합니다 (비교할 제목 정보가 없어 존재만 확인)",
        "doi_title_differs": "DOI가 가리키는 논문의 제목이 다릅니다: \"{t}\"",
        "doi_title_close": "DOI의 논문과 제목이 조금 다릅니다 (유사도 {s:.2f})",
        "doi_missing": "DOI {d} 가 어떤 등록기관에도 없습니다",
        "doi_wrong_but_found": "DOI가 틀렸지만 같은 제목의 논문은 있습니다 (실제 DOI: {d})",
        "arxiv_missing": "arXiv 번호 {a} 가 존재하지 않습니다",
        "arxiv_title_differs": "arXiv 번호가 다른 논문을 가리킵니다: \"{t}\"",
        "title_found": "같은 제목의 논문을 찾았습니다 ({src})",
        "title_similar": "제목이 비슷한 다른 논문만 있습니다 (유사도 {s:.2f}): \"{t}\"",
        "title_close_meta": "제목이 조금 다르지만 저자·연도가 맞는 논문이 있습니다 (유사도 {s:.2f})",
        "not_found": "{src}에서 일치하는 논문을 찾지 못했습니다",
        "skipped": "{src}는 요청 제한(429)으로 검색하지 못했습니다. OPENALEX_API_KEY를 설정하면 함께 검색합니다",
        "non_latin": "비영문 제목이라 해외 DB에 없을 수 있습니다 (국내 DB에서 직접 확인 필요)",
        "no_title": "제목·DOI를 읽어내지 못해 검색하지 못했습니다",
        "year": "연도 불일치: 참고문헌 {r} / 실제 {c}",
        "first_author": "첫 저자 불일치: 참고문헌 {r} / 실제 {c}",
        "author_overlap": "저자 목록 상당 부분 불일치 (일치 {k}/{n})",
        "author_absent": "실제 첫 저자({c})가 참고문헌에 없습니다",
        "year_absent": "실제 연도({c})가 참고문헌에 없습니다",
        "placeholder": "템플릿·자리표시 문구가 남아 있습니다",
        "network": "네트워크 오류로 확인하지 못했습니다: {e}",
    },
    "en": {
        "doi_ok": "DOI resolves to a real paper with a matching title",
        "doi_only": "DOI exists (no title given, so only existence was checked)",
        "doi_title_differs": "The DOI points to a paper with a different title: \"{t}\"",
        "doi_title_close": "Title differs slightly from the DOI's paper (similarity {s:.2f})",
        "doi_missing": "DOI {d} is not registered anywhere",
        "doi_wrong_but_found": "DOI is wrong, but a paper with this title exists (actual DOI: {d})",
        "arxiv_missing": "arXiv ID {a} does not exist",
        "arxiv_title_differs": "The arXiv ID points to a different paper: \"{t}\"",
        "title_found": "Found a paper with the same title ({src})",
        "title_similar": "Only a different paper with a similar title exists (similarity {s:.2f}): \"{t}\"",
        "title_close_meta": "Title differs slightly but authors/year match (similarity {s:.2f})",
        "not_found": "No matching paper in {src}",
        "skipped": "{src} could not be searched (rate-limited, HTTP 429). Set OPENALEX_API_KEY to include it",
        "non_latin": "Non-Latin title; it may simply not be indexed in these databases (check a local database)",
        "no_title": "Could not extract a title or DOI to search for",
        "year": "Year mismatch: reference {r} / actual {c}",
        "first_author": "First author mismatch: reference {r} / actual {c}",
        "author_overlap": "Author list largely differs ({k}/{n} match)",
        "author_absent": "Actual first author ({c}) does not appear in the reference",
        "year_absent": "Actual year ({c}) does not appear in the reference",
        "placeholder": "Template / placeholder text left in the reference",
        "network": "Could not check due to a network error: {e}",
    },
}

# ---------------------------------------------------------------- HTTP

_last_call = {}
_MIN_GAP = {"export.arxiv.org": 3.0}


def _throttle(host):
    gap = _MIN_GAP.get(host, 0.25)
    wait = _last_call.get(host, 0.0) + gap - time.time()
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.time()


class NetworkError(Exception):
    pass


DEBUG = bool(os.environ.get("CITECHECK_DEBUG"))
_rate_limited = set()   # hosts that answered 429; skipped for the rest of the run


def http_get(url, accept="application/json", retries=2, timeout=15):
    """Return (status, text). 404 -> (404, ''). Raises NetworkError if unreachable."""
    host = urllib.parse.urlparse(url).netloc
    last_err = None
    for attempt in range(retries):
        _throttle(host)
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode("utf-8", errors="replace")
                if DEBUG:
                    print(f"  {r.status} {time.time() - t0:.1f}s {url[:110]}", file=sys.stderr)
                return r.status, body
        except urllib.error.HTTPError as e:
            if DEBUG:
                print(f"  {e.code} {time.time() - t0:.1f}s {url[:110]}", file=sys.stderr)
            if e.code in (404, 410):
                return 404, ""
            if e.code == 429:
                _rate_limited.add(host + ("/search" if "search=" in url else ""))
                return 429, ""
            if e.code in (500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(2.0)
                continue
            return e.code, ""
        except Exception as e:  # URLError, timeout, connection reset
            last_err = e
            if DEBUG:
                print(f"  ERR {type(e).__name__} {time.time() - t0:.1f}s {url[:110]}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(1.5)
                continue
    raise NetworkError(str(last_err))


def get_json(url):
    status, text = http_get(url)
    if status == 200 and text:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------- text utils

def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def norm(s):
    s = unicodedata.normalize("NFKC", s or "")
    s = strip_accents(s).lower()
    s = re.sub(r"<[^>]+>", " ", s)          # html/jats tags
    s = re.sub(r"[{}\\$]", "", s)            # bibtex braces, latex
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def has_non_latin(s):
    for ch in s or "":
        if ch.isalpha() and ord(ch) > 0x24F:   # beyond Latin Extended-B
            return True
    return False


def title_score(a, b):
    """Similarity of two titles in [0, 1]."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    ta, tb = set(a.split()), set(b.split())
    jacc = len(ta & tb) / max(1, len(ta | tb))
    subset = 0.0
    if len(ta) >= 4 and ta <= tb:
        subset = 0.92                       # reference omits the subtitle
    elif len(tb) >= 4 and tb <= ta:
        subset = 0.92
    return max(ratio, jacc, subset)


def containment(cand_title, raw):
    """Share of the candidate title's words that appear in a free-text reference."""
    ct = norm(cand_title).split()
    if len(ct) < 3:
        return 0.0
    rt = set(norm(raw).split())
    return sum(1 for t in ct if t in rt) / len(ct)


def surname(name):
    """'Vaswani, Ashish' -> 'vaswani'; 'Ashish Vaswani' -> 'vaswani'."""
    name = (name or "").strip()
    if not name:
        return ""
    if "," in name:
        last = name.split(",")[0]
    else:
        parts = name.split()
        last = parts[-1] if parts else name
    return re.sub(r"[^a-z]", "", strip_accents(last).lower()) or norm(last)


def clean_latex(s):
    s = re.sub(r"\\[`'\^\"~=.uvHcdbtk]\s*", "", s)     # accent commands
    s = re.sub(r"\\(emph|textit|textbf|textrm|mathrm)\s*", "", s)
    s = s.replace("{", "").replace("}", "").replace("\\&", "&").replace("~", " ")
    return re.sub(r"\s+", " ", s).strip()


DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>{}]+", re.I)
ARXIV_NEW_RE = re.compile(r"(?:arxiv[:\s/.]*|abs/|pdf/)(\d{4}\.\d{4,5})(?:v\d+)?", re.I)
ARXIV_OLD_RE = re.compile(r"(?:arxiv[:\s]*|abs/)([a-z\-]+(?:\.[A-Z]{2})?/\d{7})", re.I)
YEAR_RE = re.compile(r"\b(19[5-9]\d|20[0-4]\d)\b")


def find_doi(text):
    m = DOI_RE.search(text or "")
    if not m:
        return None
    return m.group(0).rstrip(".,;)]")


def find_arxiv(text):
    for rx in (ARXIV_NEW_RE, ARXIV_OLD_RE):
        m = rx.search(text or "")
        if m:
            return m.group(1)
    return None


def guess_title(text):
    m = re.search(r"[\u201c\"]([^\u201d\"]{10,300})[\u201d\"]", text)
    if m:
        return m.group(1).strip(" ,.")
    m = re.search(r"\((?:19|20)\d{2}[a-z]?(?:,[^)]*)?\)\.?\s*(.+?)(?:\.\s|\?\s|$)", text)
    if m and len(m.group(1)) > 10:
        return m.group(1).strip()
    m = re.search(r"\b(?:19|20)\d{2}[a-z]?\.\s*(.+?)(?:\.\s|\?\s|$)", text)
    if m and len(m.group(1)) > 10:
        return m.group(1).strip()
    return None


PLACEHOLDER_RE = re.compile(
    r"firstname|lastname|first name|last name|to be (updated|added|determined)|"
    r"\btbd\b|\btba\b|\bxxx+\b|lorem ipsum|insert (title|citation|reference)|"
    r"author name|paper title|\[citation needed\]|url or arxiv", re.I)


# ---------------------------------------------------------------- parsers

def _skip_balanced(s, i):
    """s[i] == '{' ; return index just after its matching '}'."""
    depth = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _parse_fields(s):
    fields = {}
    i, n = 0, len(s)
    name_re = re.compile(r"\s*([A-Za-z][\w\-:]*)\s*=\s*")
    while i < n:
        m = name_re.match(s, i)
        if not m:
            i += 1
            continue
        name = m.group(1).lower()
        i = m.end()
        if i < n and s[i] == "{":
            j = _skip_balanced(s, i)
            val = s[i + 1:j - 1]
            i = j
        elif i < n and s[i] == '"':
            j, depth = i + 1, 0
            while j < n:
                c = s[j]
                if c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                elif c == '"' and depth == 0:
                    break
                j += 1
            val = s[i + 1:j]
            i = j + 1
        else:
            m2 = re.compile(r"[^,}\s]+").match(s, i)
            val = m2.group(0) if m2 else ""
            i = m2.end() if m2 else i + 1
        fields[name] = clean_latex(val)
    return fields


def parse_bibtex(text):
    refs = []
    head = re.compile(r"@(\w+)\s*\{")
    i = 0
    while True:
        m = head.search(text, i)
        if not m:
            break
        etype = m.group(1).lower()
        end = _skip_balanced(text, m.end() - 1)
        if etype in ("comment", "preamble", "string"):
            i = end
            continue
        body = text[m.end():end - 1]
        key, _, rest = body.partition(",")
        f = _parse_fields(rest)
        authors = [a.strip() for a in re.split(r"\s+and\s+", f.get("author", "")) if a.strip()]
        doi = f.get("doi") or find_doi(f.get("url", "")) or find_doi(f.get("note", ""))
        if doi:
            doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:)", "", doi.strip(), flags=re.I)
        arxiv = None
        if (f.get("archiveprefix", "").lower() == "arxiv" or "arxiv" in f.get("eprinttype", "").lower()) and f.get("eprint"):
            arxiv = re.sub(r"v\d+$", "", f["eprint"].strip())
        arxiv = arxiv or find_arxiv(" ".join([f.get("journal", ""), f.get("url", ""), f.get("note", ""), f.get("howpublished", "")]))
        year = None
        ym = YEAR_RE.search(f.get("year", "") or f.get("date", ""))
        if ym:
            year = int(ym.group(1))
        raw = f"{f.get('author', '')}. {f.get('title', '')}. {f.get('journal', '') or f.get('booktitle', '')} {f.get('year', '')}"
        refs.append({
            "key": key.strip(),
            "title": f.get("title"),
            "authors": authors,
            "year": year,
            "doi": doi,
            "arxiv": arxiv,
            "venue": f.get("journal") or f.get("booktitle"),
            "raw": raw.strip(),
        })
        i = end
    return refs


NUM_MARKER = re.compile(r"^\s*(?:\[(\d+)\]|(\d+)[.)])\s+")


def parse_text(text):
    """Split a plain-text reference list. Numbered lists ([1], 1.) are split at the markers and
    keep their numbers as keys; otherwise blank-line paragraphs or single lines are used."""
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    blocks = []   # (number or None, text)
    if sum(1 for ln in lines if NUM_MARKER.match(ln)) >= 2:
        cur_key, cur = None, None
        for ln in lines:
            m = NUM_MARKER.match(ln)
            if m:
                if cur:
                    blocks.append((cur_key, cur))
                cur_key, cur = (m.group(1) or m.group(2)), ln[m.end():].strip()
            elif cur is not None and ln.strip():
                cur += " " + ln.strip()          # continuation line of the same reference
            elif cur is not None:
                blocks.append((cur_key, cur))    # blank line ends the reference
                cur_key, cur = None, None
        if cur:
            blocks.append((cur_key, cur))
    else:
        paras = [p for p in re.split(r"\n\s*\n", "\n".join(lines)) if p.strip()]
        multi = sum(1 for p in paras if len([x for x in p.splitlines() if x.strip()]) > 1)
        if len(paras) > 1 and multi >= len(paras) / 2:   # mostly multi-line paragraphs
            blocks = [(None, " ".join(p.split())) for p in paras]
        else:
            blocks = [(None, ln.strip()) for ln in lines if ln.strip()]
    refs = []
    for key, b in blocks:
        b = re.sub(r"^\s*([-*\u2022])\s*", "", b)
        if len(b) < 15:
            continue
        ym = YEAR_RE.findall(b)
        refs.append({
            "key": f"[{key}]" if key else f"ref{len(refs) + 1}",
            "title": guess_title(b),
            "authors": [],
            "year": int(ym[0]) if ym else None,
            "years_in_text": sorted({int(y) for y in ym}),
            "doi": find_doi(b),
            "arxiv": find_arxiv(b),
            "venue": None,
            "raw": b,
        })
    return refs


def parse_json(text):
    data = json.loads(text)
    if isinstance(data, dict):
        data = data.get("references") or data.get("items") or []
    refs = []
    for i, d in enumerate(data):
        if isinstance(d, str):
            refs.extend(parse_text(d))
            continue
        authors = d.get("authors") or d.get("author") or []
        if isinstance(authors, str):
            authors = [a.strip() for a in re.split(r"\s+and\s+|;", authors) if a.strip()]
        year = d.get("year")
        try:
            year = int(str(year)[:4]) if year else None
        except ValueError:
            year = None
        refs.append({
            "key": d.get("key") or d.get("id") or f"ref{i + 1}",
            "title": d.get("title"),
            "authors": authors,
            "year": year,
            "doi": d.get("doi") or find_doi(d.get("url", "") or ""),
            "arxiv": d.get("arxiv") or find_arxiv(d.get("url", "") or ""),
            "venue": d.get("venue") or d.get("journal"),
            "raw": d.get("raw") or f"{'; '.join(authors)}. {d.get('title', '')}. {year or ''}",
        })
    return refs


def load_refs(path):
    with open(path, "r", encoding="utf-8-sig", errors="replace") as fh:
        text = fh.read()
    ext = os.path.splitext(path)[1].lower()
    if ext == ".bib" or re.search(r"@\w+\s*\{", text):
        return parse_bibtex(text)
    if ext == ".json":
        return parse_json(text)
    return parse_text(text)


# ---------------------------------------------------------------- sources

def _cand(source, title, authors, year, doi=None, venue=None, url=None, abstract=None):
    return {"source": source, "title": title or "", "authors": authors or [], "year": year,
            "doi": doi, "venue": venue, "url": url, "abstract": abstract}


def _crossref_item(it):
    title = (it.get("title") or [""])[0]
    authors = [a.get("family") or a.get("name") or "" for a in it.get("author", [])]
    year = None
    for k in ("issued", "published-print", "published-online", "created"):
        parts = (it.get(k) or {}).get("date-parts") or [[None]]
        if parts and parts[0] and parts[0][0]:
            year = parts[0][0]
            break
    venue = (it.get("container-title") or [None])[0]
    abstract = it.get("abstract")
    if abstract:
        abstract = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", abstract)).strip()
    doi = it.get("DOI")
    return _cand("Crossref", title, authors, year, doi, venue,
                 f"https://doi.org/{doi}" if doi else None, abstract)


def _mailto_param():
    return f"&mailto={urllib.parse.quote(MAILTO)}" if MAILTO else ""


def crossref_doi(doi):
    data = get_json(f"https://api.crossref.org/works/{urllib.parse.quote(doi, safe='/')}" +
                    (f"?mailto={urllib.parse.quote(MAILTO)}" if MAILTO else ""))
    if data and data.get("message"):
        return _crossref_item(data["message"])
    return None


def crossref_search(query, rows=5):
    q = urllib.parse.quote(query[:400])
    data = get_json(f"https://api.crossref.org/works?query.bibliographic={q}&rows={rows}{_mailto_param()}")
    items = ((data or {}).get("message") or {}).get("items") or []
    return [_crossref_item(it) for it in items if it.get("type") not in ("peer-review", "component")]


def _openalex_params():
    p = ""
    if OPENALEX_KEY:
        p += f"&api_key={urllib.parse.quote(OPENALEX_KEY)}"
    if MAILTO:
        p += f"&mailto={urllib.parse.quote(MAILTO)}"
    return p


def _openalex_abstract(inv):
    if not inv:
        return None
    pos = []
    for word, idxs in inv.items():
        for i in idxs:
            pos.append((i, word))
    return " ".join(w for _, w in sorted(pos)) or None


def _openalex_item(w):
    authors = [((a.get("author") or {}).get("display_name") or "") for a in w.get("authorships", [])]
    doi = (w.get("doi") or "").replace("https://doi.org/", "") or None
    venue = (((w.get("primary_location") or {}).get("source")) or {}).get("display_name")
    return _cand("OpenAlex", w.get("display_name") or w.get("title"), authors, w.get("publication_year"),
                 doi, venue, w.get("id"), _openalex_abstract(w.get("abstract_inverted_index")))


def openalex_doi(doi):
    if "api.openalex.org" in _rate_limited:
        return None
    data = get_json(f"https://api.openalex.org/works/doi:{urllib.parse.quote(doi, safe='/')}?" + _openalex_params().lstrip("&"))
    return _openalex_item(data) if data and data.get("id") else None


def openalex_search(query, rows=5):
    if "api.openalex.org/search" in _rate_limited:
        return []
    q = urllib.parse.quote(query[:300])
    data = get_json(f"https://api.openalex.org/works?search={q}&per-page={rows}{_openalex_params()}")
    return [_openalex_item(w) for w in (data or {}).get("results", [])]


def datacite_doi(doi):
    data = get_json(f"https://api.datacite.org/dois/{urllib.parse.quote(doi, safe='/')}")
    attrs = ((data or {}).get("data") or {}).get("attributes")
    if not attrs:
        return None
    title = ((attrs.get("titles") or [{}])[0]).get("title")
    authors = [c.get("familyName") or c.get("name") or "" for c in attrs.get("creators", [])]
    desc = None
    for d in attrs.get("descriptions") or []:
        if d.get("descriptionType") == "Abstract":
            desc = d.get("description")
            break
    return _cand("DataCite", title, authors, attrs.get("publicationYear"), doi,
                 attrs.get("publisher"), f"https://doi.org/{doi}", desc)


def doi_registered(doi):
    status, text = http_get(f"https://doi.org/api/handles/{urllib.parse.quote(doi, safe='/')}")
    if status == 200:
        try:
            return json.loads(text).get("responseCode") == 1
        except json.JSONDecodeError:
            return True
    return False


def arxiv_lookup(arxiv_id):
    status, text = http_get(f"https://export.arxiv.org/api/query?id_list={urllib.parse.quote(arxiv_id)}",
                            accept="application/atom+xml")
    if status != 200 or not text:
        return None
    ns = {"a": "http://www.w3.org/2005/Atom"}
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None
    entry = root.find("a:entry", ns)
    if entry is None:
        return None
    title = re.sub(r"\s+", " ", (entry.findtext("a:title", default="", namespaces=ns))).strip()
    if not title or title.lower() == "error":
        return None
    authors = [a.findtext("a:name", default="", namespaces=ns) for a in entry.findall("a:author", ns)]
    pub = entry.findtext("a:published", default="", namespaces=ns)
    year = int(pub[:4]) if pub[:4].isdigit() else None
    summary = re.sub(r"\s+", " ", entry.findtext("a:summary", default="", namespaces=ns)).strip()
    return _cand("arXiv", title, authors, year, f"10.48550/arXiv.{arxiv_id}", "arXiv",
                 f"https://arxiv.org/abs/{arxiv_id}", summary or None)


# ---------------------------------------------------------------- comparison

def meta_issues(ref, cand, msg):
    """Author / year problems between a reference and the matched paper."""
    issues = []
    cand_last = [surname(a) for a in cand["authors"] if a]
    cand_last = [c for c in cand_last if c]
    if ref.get("authors"):
        ref_last = [surname(a) for a in ref["authors"] if a and a.lower() not in ("others", "et al", "et al.")]
        ref_last = [r for r in ref_last if r]
        if ref_last and cand_last and not has_non_latin(" ".join(cand["authors"])):
            if ref_last[0] not in cand_last[:5]:
                issues.append(msg["first_author"].format(r=ref["authors"][0], c=cand["authors"][0]))
            elif len(ref_last) >= 2:
                k = sum(1 for r in ref_last if r in cand_last)
                if k / len(ref_last) < 0.5:
                    issues.append(msg["author_overlap"].format(k=k, n=len(ref_last)))
    elif ref.get("raw") and cand_last and not has_non_latin(" ".join(cand["authors"])):
        raw_tokens = set(norm(ref["raw"]).split())
        if cand_last[0] not in raw_tokens:
            issues.append(msg["author_absent"].format(c=cand["authors"][0]))
    cy = cand.get("year")
    if cy:
        if ref.get("years_in_text") is not None and not ref.get("authors"):
            if ref["years_in_text"] and all(abs(y - cy) > 1 for y in ref["years_in_text"]):
                issues.append(msg["year_absent"].format(c=cy))
        elif ref.get("year") and abs(ref["year"] - cy) > 1:
            issues.append(msg["year"].format(r=ref["year"], c=cy))
    return issues


def score_against(ref, cand):
    if ref.get("title"):
        return title_score(ref["title"], cand["title"])
    return containment(cand["title"], ref.get("raw", ""))


def best_by_title(ref):
    if ref.get("authors") or not ref.get("raw"):
        # structured entry: title + first author + year + venue
        parts = [ref.get("title") or ""]
        if ref.get("authors"):
            parts.append(surname(ref["authors"][0]))
        if ref.get("year"):
            parts.append(str(ref["year"]))
        if ref.get("venue"):
            parts.append(ref["venue"])
        query = " ".join(p for p in parts if p)
    else:
        # free-text citation: Crossref's bibliographic search is built for whole citation strings
        query = ref["raw"]
    short_title = len(norm(ref.get("title") or "").split()) <= 3
    cands, searched, skipped = [], [], []
    try:
        cands += crossref_search(query, rows=10 if short_title else 5)
        searched.append("Crossref")
    except NetworkError:
        skipped.append("Crossref")
    try:
        found = openalex_search(ref.get("title") or ref.get("raw") or "")
        if "api.openalex.org/search" in _rate_limited:
            skipped.append("OpenAlex")
        else:
            searched.append("OpenAlex")
            cands += found
    except NetworkError:
        skipped.append("OpenAlex")
    # Rank by title similarity; among near-identical titles prefer the one whose
    # authors/year agree with the reference (many papers share short titles).
    best, best_key, best_s = None, None, 0.0
    for c in cands:
        s = score_against(ref, c)
        n_issues = len(meta_issues(ref, c, MSG["en"]))
        key = (s >= 0.9, -n_issues, s)
        if best_key is None or key > best_key:
            best, best_key, best_s = c, key, s
    return best, best_s, (searched, skipped)


def verify(ref, msg):
    out = {"status": None, "reasons": [], "match": None}
    text_all = " ".join(str(x) for x in [ref.get("title"), " ".join(ref.get("authors") or []), ref.get("raw")] if x)
    if PLACEHOLDER_RE.search(text_all):
        out["status"] = "PLACEHOLDER"
        out["reasons"].append(msg["placeholder"])
        return out

    # 1) arXiv ID
    arxiv_id = ref.get("arxiv")
    if not arxiv_id and ref.get("doi") and ref["doi"].lower().startswith("10.48550/arxiv."):
        arxiv_id = ref["doi"].split(".", 2)[-1]
    if arxiv_id:
        try:
            cand = arxiv_lookup(arxiv_id)
        except NetworkError:
            cand = None
        if cand is None:   # arXiv API is slow at times; arXiv DOIs are also registered at DataCite
            try:
                cand = datacite_doi(f"10.48550/arXiv.{arxiv_id}")
            except NetworkError:
                cand = None
        if cand is None:
            out["reasons"].append(msg["arxiv_missing"].format(a=arxiv_id))
        else:
            has_title = bool(ref.get("title"))
            s = score_against(ref, cand)
            if (has_title and s < 0.6) or (not has_title and ref.get("raw") and s < 0.5):
                out["status"] = "ID_MISMATCH"
                out["reasons"].append(msg["arxiv_title_differs"].format(t=cand["title"]))
                out["match"] = cand
                return out
            issues = meta_issues(ref, cand, msg)
            out["match"] = cand
            if has_title and s < 0.9:
                issues.insert(0, msg["doi_title_close"].format(s=s))
            out["status"] = "METADATA_MISMATCH" if issues else "VERIFIED"
            out["reasons"] = issues or [msg["title_found"].format(src="arXiv")]
            return out

    # 2) DOI
    doi = ref.get("doi")
    if doi:
        cand = crossref_doi(doi) or datacite_doi(doi)
        if cand is None and doi_registered(doi):
            cand = openalex_doi(doi)
            if cand is None:   # registered but no metadata we can read
                out["status"] = "VERIFIED"
                out["reasons"].append(msg["doi_only"])
                out["match"] = _cand("doi.org", "", [], None, doi, None, f"https://doi.org/{doi}")
                return out
        if cand is not None:
            out["match"] = cand
            if not ref.get("title") and not ref.get("raw"):
                out["status"] = "VERIFIED"
                out["reasons"].append(msg["doi_only"])
                return out
            s = score_against(ref, cand)
            if s < 0.6:
                out["status"] = "ID_MISMATCH"
                out["reasons"].append(msg["doi_title_differs"].format(t=cand["title"]))
                return out
            issues = meta_issues(ref, cand, msg)
            if ref.get("title") and s < 0.9:
                issues.insert(0, msg["doi_title_close"].format(s=s))
            out["status"] = "METADATA_MISMATCH" if issues else "VERIFIED"
            out["reasons"] = issues or [msg["doi_ok"]]
            return out
        out["reasons"].append(msg["doi_missing"].format(d=doi))

    # 3) title search
    if not (ref.get("title") or ref.get("raw")):
        out["status"] = "UNVERIFIABLE"
        out["reasons"].append(msg["no_title"])
        return out
    best, s, (searched, skipped) = best_by_title(ref)
    title_for_lang = ref.get("title") or ref.get("raw") or ""
    if best is not None and s >= 0.9:
        out["match"] = best
        issues = meta_issues(ref, best, msg)
        if doi:   # the given DOI was wrong but the paper exists
            issues.insert(0, msg["doi_wrong_but_found"].format(d=best.get("doi")))
        out["status"] = "METADATA_MISMATCH" if issues else "VERIFIED"
        out["reasons"] = (out["reasons"] if not doi else []) + (issues or [msg["title_found"].format(src=best["source"])])
        return out
    if best is not None and s >= 0.75:
        issues = meta_issues(ref, best, msg)
        out["match"] = best
        if not issues and (ref.get("authors") or ref.get("year")):
            out["status"] = "METADATA_MISMATCH"
            out["reasons"].append(msg["title_close_meta"].format(s=s))
        else:
            out["status"] = "SIMILAR_ONLY"
            out["reasons"].append(msg["title_similar"].format(s=s, t=best["title"]))
            out["reasons"].extend(issues)
        return out
    if has_non_latin(title_for_lang):
        out["status"] = "UNVERIFIABLE"
        out["reasons"].append(msg["non_latin"])
        return out
    if not searched:
        out["status"] = "ERROR"
        out["reasons"].append(msg["network"].format(e="no database could be searched"))
        return out
    out["status"] = "NOT_FOUND"
    out["reasons"].append(msg["not_found"].format(src=" · ".join(searched)))
    if skipped:
        out["reasons"].append(msg["skipped"].format(src=", ".join(skipped)))
    if best is not None and s >= 0.5:
        out["reasons"].append(msg["title_similar"].format(s=s, t=best["title"]))
    return out


def europepmc_abstract(doi):
    """Abstract from Europe PMC (covers PubMed, incl. many Nature/Science papers)."""
    q = urllib.parse.quote(f'DOI:"{doi}"')
    data = get_json("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
                    f"query={q}&resultType=core&format=json&pageSize=1")
    res = (((data or {}).get("resultList") or {}).get("result")) or []
    if res and res[0].get("abstractText"):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", res[0]["abstractText"])).strip()
    return None


def fetch_abstract(match):
    """Best-effort abstract for a matched paper."""
    if not match:
        return None, None
    if match.get("abstract"):
        return match["abstract"], match["source"]
    doi = match.get("doi")
    if doi:
        try:
            oa = openalex_doi(doi)
            if oa and oa.get("abstract"):
                return oa["abstract"], "OpenAlex"
            cr = crossref_doi(doi)
            if cr and cr.get("abstract"):
                return cr["abstract"], "Crossref"
            pm = europepmc_abstract(doi)
            if pm:
                return pm, "Europe PMC"
        except NetworkError:
            return None, None
    return None, None


# ---------------------------------------------------------------- report

def md_escape(s):
    return (s or "").replace("|", "\\|").replace("\n", " ")


def write_reports(results, out_dir, lang, src_name):
    os.makedirs(out_dir, exist_ok=True)
    li = 0 if lang == "ko" else 1
    counts = {k: 0 for k in STATUS}
    for r in results:
        counts[r["status"]] += 1
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(os.path.join(out_dir, "citation_report.json"), "w", encoding="utf-8") as fh:
        json.dump({"tool": f"citation-check {VERSION}", "input": src_name, "checked_at": now,
                   "counts": counts, "results": results}, fh, ensure_ascii=False, indent=2)

    L = []
    if lang == "ko":
        L.append("# 인용 검증 결과\n")
        L.append(f"- 입력: `{src_name}` · 검사 시각: {now} · 참고문헌 {len(results)}개")
        L.append("- 조회한 곳: Crossref, OpenAlex, arXiv, DataCite, doi.org (무료 공개 API)\n")
        L.append("| 판정 | 개수 |\n|---|---|")
    else:
        L.append("# Citation check report\n")
        L.append(f"- Input: `{src_name}` · Checked: {now} · {len(results)} references")
        L.append("- Sources: Crossref, OpenAlex, arXiv, DataCite, doi.org (free public APIs)\n")
        L.append("| Status | Count |\n|---|---|")
    for k in SEVERITY:
        if counts[k]:
            L.append(f"| {STATUS[k][li]} (`{k}`) | {counts[k]} |")
    L.append("")

    problems = [r for r in results if r["status"] not in ("VERIFIED",)]
    problems.sort(key=lambda r: SEVERITY.index(r["status"]))
    L.append("## 확인이 필요한 항목\n" if lang == "ko" else "## Items needing attention\n")
    if not problems:
        L.append("없음.\n" if lang == "ko" else "None.\n")
    else:
        hdr = "| # | 키 | 판정 | 이유 | 찾은 논문 |" if lang == "ko" else "| # | Key | Status | Why | Matched paper |"
        L.append(hdr + "\n|---|---|---|---|---|")
        for r in problems:
            m = r.get("match") or {}
            found = ""
            if m.get("title"):
                found = f"{md_escape(m['title'])} ({m.get('year') or '?'})"
                if m.get("doi"):
                    found += f" [doi:{m['doi']}](https://doi.org/{m['doi']})"
            L.append(f"| {r['index']} | {md_escape(r['key'])} | {STATUS[r['status']][li]} | "
                     f"{md_escape('; '.join(r['reasons']))} | {found} |")
        L.append("")

    L.append("## 전체 목록\n" if lang == "ko" else "## All references\n")
    hdr = "| # | 키 | 판정 | 참고문헌 제목 |" if lang == "ko" else "| # | Key | Status | Reference title |"
    L.append(hdr + "\n|---|---|---|---|")
    for r in results:
        t = r["input"].get("title") or (r["input"].get("raw") or "")[:120]
        L.append(f"| {r['index']} | {md_escape(r['key'])} | {STATUS[r['status']][li]} | {md_escape(t)} |")
    L.append("")
    if lang == "ko":
        L.append("> 주의: '찾을 수 없음'은 위 DB에 없다는 뜻이지 곧바로 가짜라는 뜻은 아닙니다 "
                 "(책·학위논문·국내 학술지·최신 논문은 빠져 있을 수 있음). '확인됨'은 논문이 존재한다는 뜻일 뿐, "
                 "인용한 문장의 내용이 맞다는 뜻은 아닙니다.")
    else:
        L.append("> Note: 'Not found' means absent from these databases, not proof of fabrication "
                 "(books, theses, regional journals and very recent papers may be missing). 'Verified' means "
                 "the paper exists, not that it supports the sentence citing it.")
    with open(os.path.join(out_dir, "citation_report.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    return counts


# ---------------------------------------------------------------- main

def main():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="Check that references exist (Crossref/OpenAlex/arXiv).")
    ap.add_argument("input", help=".bib, .txt/.md (one reference per line) or .json")
    ap.add_argument("--out", default="citation_check", help="output directory")
    ap.add_argument("--abstracts", action="store_true", help="also fetch abstracts for claim checking")
    ap.add_argument("--lang", choices=["ko", "en"], default="ko")
    ap.add_argument("--limit", type=int, default=0, help="check only the first N references")
    args = ap.parse_args()

    refs = load_refs(args.input)
    if args.limit:
        refs = refs[:args.limit]
    if not refs:
        print("No references found in input.", file=sys.stderr)
        sys.exit(1)
    msg = MSG[args.lang]
    li = 0 if args.lang == "ko" else 1
    results = []
    for i, ref in enumerate(refs, 1):
        try:
            v = verify(ref, msg)
        except NetworkError as e:
            v = {"status": "ERROR", "reasons": [msg["network"].format(e=e)], "match": None}
        rec = {"index": i, "key": ref["key"], "status": v["status"],
               "status_label": STATUS[v["status"]][li], "reasons": v["reasons"],
               "input": {k: ref.get(k) for k in ("title", "authors", "year", "doi", "arxiv", "venue", "raw")},
               "match": None}
        m = v.get("match")
        if m:
            rec["match"] = {k: m.get(k) for k in ("source", "title", "authors", "year", "doi", "venue", "url")}
        if args.abstracts and v["status"] in ("VERIFIED", "METADATA_MISMATCH"):
            ab, src = fetch_abstract(m)
            rec["abstract"] = ab
            rec["abstract_source"] = src
        results.append(rec)
        print(f"[{i}/{len(refs)}] {ref['key']}: {STATUS[v['status']][li]}", file=sys.stderr)

    counts = write_reports(results, args.out, args.lang, os.path.basename(args.input))
    summary = ", ".join(f"{STATUS[k][li]} {counts[k]}" for k in SEVERITY if counts[k])
    print(f"\n{len(results)} references -> {summary}")
    print(f"Report: {os.path.join(args.out, 'citation_report.md')}")


if __name__ == "__main__":
    main()
