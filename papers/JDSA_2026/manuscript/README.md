# Anonymous manuscript sources

This directory contains the anonymous manuscript and Online Resource 1. The
identified title page and confidential related-publication disclosure are
separate editorial files and must not accompany the anonymous review copy.

Build with a recent TeX Live distribution, pdfLaTeX and BibTeX:

```bash
bash build.sh
```

Required packages include the supplied Springer Nature `sn-jnl.cls` and
`sn-basic.bst`, graphicx, amsmath, amssymb, booktabs, tabularx, array,
ragged2e, longtable, float, TikZ, algorithm, algorithmicx, algpseudocode,
seqsplit and placeins. The class supplies hyperref and natbib. No custom
fonts, shell escape, model access or scientific computation is required.
Build products and logs go to `build/`; the two final PDFs are copied here.
The source archive also contains flattened paths for submission systems.

The manuscript uses numbered citations, decimal headings, numbered displayed
equations and six keywords. Figures are vector material. Existing numerical
plots preserve observations and vector data paths. Readability variants enlarge
lettering and rearrange source-scale/opportunity panels; the original plots are
retained. Forest panels use a larger two-row arrangement.
The comparison diagram is editable TikZ. Tables use additional row spacing.

An anonymized supporting evidence/code archive is prepared separately for
editorial or reviewer requests. It is not required to compile these documents.
No external reviewer-delivery channel or anonymous download link has been established. Permanent links for this package remain planned, subject to permissions. Ordinary
scholarly references, including relevant prior work and the earlier public
preprint, are retained neutrally; anonymity cannot prevent discovery of a
public research lineage through those citations.

This is an author-review draft. Local compilation and anonymity checks do not
constitute journal submission clearance or permission to redistribute restricted
source material.
