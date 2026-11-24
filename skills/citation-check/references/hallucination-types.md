# Types of problematic references

Read this when explaining results to the user, or when a case does not fit the status labels neatly.

## Taxonomy from 100 fabricated citations in NeurIPS 2025 accepted papers

Ansari (2026), "Compound Deception in Elite Peer Review" (arXiv:2602.05930), coded the 100 fabricated citations that GPTZero found in 53 NeurIPS 2025 accepted papers:

| Type | Share | What it looks like | How this skill reports it |
|---|---|---|---|
| Total fabrication | 66% | Authors, title, venue and identifiers all invented | `NOT_FOUND` |
| Partial attribute corruption | 27% | Real and fake mixed: real authors on a non-existent title, a real title with fake authors, the right venue in the wrong year | `METADATA_MISMATCH` or `SIMILAR_ONLY` |
| Identifier hijacking | 4% | A valid DOI or arXiv ID that resolves to a different real paper | `ID_MISMATCH` |
| Placeholder | 2% | "Firstname Lastname", "URL or arXiv ID to be updated" | `PLACEHOLDER` |
| Semantic hallucination | 1% | A plausible invented title in the right field | `NOT_FOUND` or `SIMILAR_ONLY` |

Identifier hijacking is why the script compares the DOI's real title with the cited title, instead of only checking that the DOI exists.

## How common the problem is

- Russinovich et al. (2026), "Phantom References" (arXiv:2607.00738), checked 2.6 million references in 48,095 accepted papers. In 2025, 18.7% (ICLR) to 34.9% (USENIX Security) of papers had at least one flagged reference. At the reference level the rate was 0.4–0.8%. These are automatic flags and include some false positives.
- Walters & Wilder (2023, Scientific Reports) found 55% of GPT-3.5 and 18% of GPT-4 citations fabricated, and substantive errors in 43% and 24% of the real ones.
- Rao et al. (2026, arXiv:2604.03173) found 3–13% of citation URLs from commercial LLMs and deep-research agents hallucinated. Deep-research agents were worse (10.7%) than search-augmented chat (4.8%), largely because they cite many more sources.

## Humans make the second kind of error too

Claim-support errors predate AI. A meta-analysis of medical journals (Jergas & Baethge 2015, PeerJ) found about one in five citations problematic and about one in eight seriously wrong. A cited paper did not say what it was cited for. Stage 1 errors (non-existent papers) are largely an AI-era problem. Stage 2 errors (real paper, wrong claim) are an old one that AI does not fix.

## Limits of automatic checking

- Database coverage: books, theses, technical reports, regional journals (Korean, Chinese, etc.) and papers from the last few weeks may be missing.
- Short or generic titles ("Deep learning") match many papers. The script prefers the candidate whose authors and year agree, but tell the user when a match rests on a short title.
- Existing tools trade sensitivity for false alarms. Badalova & Mayr (2026, arXiv:2607.22693) compared five checkers on 104 references: the most sensitive caught 32 of 33 problems but also flagged 36 of 71 good references. Treat flags as "look here", not as verdicts.
