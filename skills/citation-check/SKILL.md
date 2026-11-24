---
name: citation-check
description: Check whether the references in a paper, thesis, report, BibTeX file or AI-generated answer really exist and are cited correctly, using free public databases (Crossref, OpenAlex, arXiv, DataCite). Flags fabricated references, wrong authors/years, DOIs or arXiv IDs that point to a different paper, placeholders, and only-similar-title matches, then checks whether each source's abstract supports the sentence citing it. Use this whenever the user wants to verify, audit, proofread or sanity-check citations, a bibliography, a .bib file or a reference list, including requests like "are these papers real?", "AI가 준 참고문헌 진짜야?", "인용 검증", "참고문헌 확인", "가짜 인용 찾아줘", "hallucinated citations", "check my references before submission", even if the word "verify" never appears.
license: MIT
---

# Citation check

Language models (and tired humans) produce references that look right but are not: invented papers, real titles with the wrong authors, real DOIs attached to a different paper. Peer review does not reliably catch these. Accepted papers at top venues have shipped with fabricated references. This skill checks references against public bibliographic databases in two stages:

1. **Existence** (automatic, by script): does the paper exist, and do the title, authors, year and identifier agree?
2. **Claim support** (your judgment, from abstracts): does the cited paper's abstract support the sentence that cites it?

Stage 1 is fully scripted so results are reproducible. Stage 2 needs reading comprehension, so you do it, but only from the fetched abstract text, never from memory. That way every verdict can be traced to evidence the user can see.

## Step 1: Get the references into a file

The script reads three formats. It detects the format from the file content.

- **BibTeX** (`.bib`): use as is.
- **Plain text** (`.txt` / `.md`): one reference per line, or references separated by blank lines. Any style works (APA, IEEE, ACM). In a numbered list (`[12] ...` or `12. ...`), only the numbered entries are read and each keeps its number as its key (`[12]`). That makes it easy to match in-text markers in step 4, and a manuscript whose reference list is numbered can be passed as is.
- **JSON**: a list of `{"key", "title", "authors": [...], "year", "doi"}` objects.

For anything else, copy the reference list into `refs.txt` yourself, one reference per line, keeping the original numbers or keys. This covers PDFs, Word files, pasted chat text, and manuscripts with unnumbered reference lists. Keep every DOI, arXiv ID and URL, because identifiers make the check much stronger. If the user also wants claim checking, keep the manuscript text available too.

## Step 2: Run the existence check

```bash
python "${CLAUDE_SKILL_DIR}/scripts/check_refs.py" refs.bib --out citation_check --abstracts
```

- `${CLAUDE_SKILL_DIR}` is this skill's folder. If your agent does not substitute it, use the `scripts/` folder next to this SKILL.md.
- Use whichever Python 3.8+ is installed (`python3`, `python`, or `py -3` on Windows). Only the standard library is needed. If none is on PATH, look for a conda install (e.g. `~/miniconda3/python.exe`, `~/anaconda3/bin/python`). If there is still none, ask the user to install Python rather than rewriting the script.
- `--abstracts` also downloads abstracts for stage 2. Leave it off if the user only wants an existence check.
- `--lang en` writes the report in English. The default is Korean.
- Expect about 1 to 3 seconds per reference. arXiv lookups are deliberately slowed to respect the arXiv API's rate limit.

Only titles, authors, years and identifiers are sent to the public APIs. The manuscript itself is never sent. Tell the user this if they ask about privacy.

The script writes `citation_check/citation_report.md` (for people) and `citation_check/citation_report.json` (for you). Read the JSON.

## Step 3: Interpret the results

Each reference gets one status. For what each problem type looks like and how often it occurs, see `references/hallucination-types.md`.

| Status | Meaning | Suggested action for the user |
|---|---|---|
| `VERIFIED` 확인됨 | A paper with this title (and matching authors/year) exists | None for stage 1 |
| `METADATA_MISMATCH` 정보 일부 틀림 | The paper exists, but the authors, year, title or DOI in the reference are wrong | Replace with the correct details shown in `match` |
| `ID_MISMATCH` 식별자 불일치 | The DOI/arXiv ID is real but belongs to a different paper | Serious: either the identifier or the whole reference is wrong |
| `SIMILAR_ONLY` 비슷한 논문만 있음 | Only a paper with a similar title exists | Ask whether that paper was the one intended; if not, likely fabricated |
| `NOT_FOUND` 찾을 수 없음 | Nothing matching in Crossref/OpenAlex | Likely fabricated, but books, theses, regional journals and very new papers can be missing. Search Google Scholar or a library catalog before deleting |
| `UNVERIFIABLE` 확인 불가 | Non-Latin title or no searchable information | Check a regional database (e.g. KCI, RISS, DBpia for Korean papers) |
| `PLACEHOLDER` 자리표시 문구 | Template text such as "Firstname Lastname" | Fill in or remove |
| `ERROR` 조회 오류 | Network problem | Re-run later |

Two cautions to pass on, because users tend to over-read the labels:
- `NOT_FOUND` is evidence, not proof, of fabrication. The reason text says which databases were actually searched. If one was skipped (e.g. OpenAlex rate-limited), say so. If you have a web search tool, run one quick search for the exact title of each `NOT_FOUND` item and report what you found. Otherwise suggest that the user search Google Scholar.
- `VERIFIED` only means the paper exists. It says nothing about whether it supports the claim. That is stage 2.

## Step 4: Check claim support (when the manuscript is available)

For each reference whose paper exists (`VERIFIED` or `METADATA_MISMATCH`):

1. Find every sentence in the manuscript that cites it. Citation markers can look like `\cite{key}`, `[@key]`, `[12]` or `(Kim, 2020)`. The keys in the report keep the reference list's own numbers and BibTeX keys.
2. Compare the specific claim in that sentence with the `abstract` in `citation_report.json`. The script tries the matched record, OpenAlex, Crossref and Europe PMC.
3. Give one verdict per (sentence, reference) pair:
   - **지지됨 Supported**: the abstract states or directly implies the claim.
   - **부분 지지 Partly supported**: related, but the claim overstates, generalizes, or changes a number or condition.
   - **지지 안 됨 Not supported**: the abstract is about something else, or contradicts the claim.
   - **판단 불가 Can't tell from abstract**: the claim concerns details an abstract would not contain (a specific table value, a method detail), or no abstract was available.
4. Quote, or closely paraphrase, the part of the abstract your verdict rests on, and name where the abstract came from (`abstract_source`).

References that do not exist (`NOT_FOUND`, `ID_MISMATCH`, `PLACEHOLDER`) cannot support anything. List them in the claim table as "판단 불가: 문헌 확인 안 됨" and refer to stage 1.

Prefer **판단 불가** over guessing. An abstract is a thin summary, and a false "not supported" can wrongly accuse the author. Do not fill gaps from what you remember about the paper. The verdict is only useful if the evidence is on the page. If no abstract was found and you can fetch one from another public source (e.g. the publisher's page or PubMed), you may use it, but name that source.

## Step 5: Report to the user

Lead with the counts, then the problems ordered by severity: `ID_MISMATCH`, `NOT_FOUND`, `PLACEHOLDER`, `SIMILAR_ONLY`, `METADATA_MISMATCH`, `UNVERIFIABLE`. For each problem give the reference, what is wrong, the correct details if found, and the suggested action. If you did stage 2, add a table:

| Sentence (short) | Reference | Verdict | Evidence from abstract |
|---|---|---|---|

Point the user to `citation_check/citation_report.md` for the full list. Keep the summary short. The user wants to know what to fix.

## Optional settings

- `CROSSREF_MAILTO=you@example.org`: adds the user's e-mail to API requests, which Crossref and OpenAlex reward with faster, more reliable service. Only set it if the user provides their e-mail for this purpose.
- `OPENALEX_API_KEY=...`: OpenAlex limits keyword search without a key (HTTP 429). The script then searches Crossref alone, which works but finds slightly fewer matches, and the report says so.
- `CITECHECK_DEBUG=1`: prints every API request with its status code and time, which helps when results look wrong.
