# CombMNZ Continuation Assessment

**Decision:** DO_NOT_ADD: CombMNZ vs CombSUM macro deltas are tiny under this unambiguous definition; expanding baselines would add volume without strengthening the repair thesis.

**Definition used:** CombMNZ(d) = CombSUM(d) * nz(d), where CombSUM sums per-ranker min-max normalized scores over the candidate pool and nz(d) counts rankers with a nonzero contribution after that normalization (missing -> 0).

- scidocs: CombSUM=0.1866, CombMNZ=0.1884, Δ=+0.0018 (n=120)
- fiqa: CombSUM=0.0492, CombMNZ=0.0462, Δ=-0.0031 (n=120)
- hotpotqa: CombSUM=0.3320, CombMNZ=0.3320, Δ=+0.0000 (n=52)
- bright: CombSUM=0.1606, CombMNZ=0.1606, Δ=+0.0000 (n=50)

Ambiguities remain around nonzero coding and tie-breaking; paper baseline family left unchanged. Numbers are exploratory only and are not written into main.tex.
