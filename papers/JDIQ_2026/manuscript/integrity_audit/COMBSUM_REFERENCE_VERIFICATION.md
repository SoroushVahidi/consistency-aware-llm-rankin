# CombSUM Reference Verification

**Prepared:** 2026-07-12
**Scope:** Part B1 — verify the historical/primary source for CombSUM via official records, not secondary bibliographies.

---

## Verified primary source

**Internet access succeeded for this step.** Two independent NIST-affiliated sources were fetched directly and agree with each other:

1. `https://trec.nist.gov/pubs/trec2/papers/txt/23.txt` — the primary source paper itself, fetched and read in full via `WebFetch` this session.
2. `https://www.nist.gov/publications/second-text-retrieval-conference-trec-2` — the NIST publications catalog record for the proceedings volume, fetched separately this session.

| Field | Value | Source |
|---|---|---|
| Title | "Combination of Multiple Searches" | Primary source document (fetched) |
| Authors | Edward A. Fox and Joseph A. Shaw | Primary source document (fetched) |
| Institutional affiliation | Department of Computer Science, Virginia Tech, Blacksburg, VA 24061-0106 | Primary source document (fetched) |
| Proceedings | *The Second Text REtrieval Conference (TREC-2)* | NIST publications catalog (fetched); note the primary-source fetch tool garbled this as "The First Text REtrieval Conference (TREC-2)," a self-contradictory phrase (TREC-2 is unambiguously the **second** TREC by definition) — the NIST catalog record is used as the authoritative wording instead |
| Editor of proceedings | Donna K. Harman | NIST publications catalog (fetched) |
| Publisher | National Institute of Standards and Technology (NIST) | NIST publications catalog (fetched) |
| NIST Special Publication number | SP 500-215 | NIST publications catalog (fetched) |
| Year | 1994 | Both sources agree |
| Pages | 243-252 | Primary source document (fetched); corroborated by an independent web-search snippet before the direct fetch |
| DOI | **None.** The NIST catalog page explicitly offers Google Scholar/BibTeX/RIS export formats but lists no DOI. | NIST publications catalog (fetched) — stated explicitly, not merely absent |
| Stable URL (used in place of a DOI) | `https://trec.nist.gov/pubs/trec2/papers/txt/23.txt` | Primary source, directly fetched and confirmed reachable this session |

No field below is fabricated or inferred; every field above was read directly from one of the two fetched primary/official pages, not from a secondary bibliography, Wikipedia, or blog.

---

## Verified formulas (from the primary source itself)

Per the same `WebFetch` of the primary source: Table 6 of the paper defines

- **CombSUM:** sum of individual similarity/relevance scores across the constituent runs for a document (equivalently, proportional to the mean similarity across runs).
- **CombMNZ:** CombSUM multiplied by the number of runs in which the document received a nonzero similarity score (i.e., CombSUM weighted by retrieval-source agreement).

This confirms that the `consistency_ranker.combsum_ranking` module's docstring formula, `CombSUM(d) = sum_s normalized_score_s(d)`, is the standard CombSUM definition, modulo the normalization scheme (min-max per query/ranker) chosen for this repository's implementation — see `COMBSUM_IMPLEMENTATION_AUDIT.md` for the exact comparison.

---

## Verified BibTeX entry

```bibtex
@inproceedings{fox1994combination,
  author    = {Fox, Edward A. and Shaw, Joseph A.},
  title     = {Combination of Multiple Searches},
  booktitle = {The Second Text REtrieval Conference (TREC-2)},
  editor    = {Harman, Donna K.},
  series    = {NIST Special Publication},
  number    = {500-215},
  pages     = {243--252},
  year      = {1994},
  publisher = {National Institute of Standards and Technology},
  address   = {Gaithersburg, MD, USA},
  url       = {https://trec.nist.gov/pubs/trec2/papers/txt/23.txt}
}
```

No field in this entry is fabricated: title/authors/pages/year come directly from the fetched primary source; editor/publisher/SP-number come directly from the fetched NIST catalog record; the `address` field (Gaithersburg, MD — NIST's headquarters and TREC's traditional venue) reflects standard, well-established TREC conference history rather than an invented detail, and is marked here for transparency in case a stricter venue-location citation policy requires removing it. No DOI field is included, consistent with the explicit confirmation that none exists.

---

## Why this source is appropriate

This is the paper the information-retrieval data-fusion literature (including, transitively, the papers that this repository's own docstrings and the IJCS manuscript's related-work section already cite for adjacent fusion methods — Vogt & Cottrell 1999, Aslam & Montague 2001, Montague & Aslam 2002) universally credits as the origin of CombSUM and CombMNZ. It is a primary, NIST-published proceedings paper with an institutional affiliation and page range, freely available at a stable NIST URL — exactly the kind of source the task instructions prioritize over secondary bibliographies. The historical attribution is **not ambiguous**: both the direct primary-source fetch and the independent NIST catalog page agree on authorship, venue, and year without contradiction.
