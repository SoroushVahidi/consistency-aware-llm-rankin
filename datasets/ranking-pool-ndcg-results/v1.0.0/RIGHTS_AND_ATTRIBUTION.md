# Rights, source credits and scope

Soroush Vahidi licenses only the independently generated numerical measurements, original analyses, metadata and documentation in this release under CC BY 4.0. The original validation software is MIT. Original benchmark text, annotations/qrels, rankings, raw identifiers and corpora are not distributed or relicensed here.

The [FiQA-2018 original challenge page](https://sites.google.com/view/fiqa/home) states that its Task 2 training and test **data** are available only for noncommercial use. This study used them for noncommercial research. The page does not state a separate limit on publication or licensing of independently computed text-free evaluation results, and no additional access agreement was identified in the scoped records. The [BEIR FiQA mirror](https://huggingface.co/datasets/BeIR/fiqa) labels its distribution CC BY-SA 4.0; that label does not override original-source conditions. Reusers who obtain FiQA source data must determine their own permission under its terms. This CC BY 4.0 grant covers only this author's result compilation, not FiQA data.

The same distinction applies to the other source benchmarks. These tables do not contain protected text or a substantial extraction of source annotations or their selection/arrangement. No claim is made that raw corpora can be redistributed under this release license. Dataset names and query-ID hashes are experiment linkage metadata, not source text; the hashes may be brute-force linkable to known public IDs.

| Benchmark or tool | Credit and source | Source terms noted for underlying material |
|---|---|---|
| FiQA-2018 | Maia et al. (2018), [original challenge](https://sites.google.com/view/fiqa/home); BEIR-format distribution by Thakur et al. | Original challenge noncommercial data-use notice; BEIR mirror card CC BY-SA 4.0. The challenge page acknowledges SSIX Horizon 2020 project grant 645425 for the source benchmark. |
| SciDocs/SPECTER | Cohan et al. (2020), [original repository](https://github.com/allenai/scidocs), BEIR-format distribution | Original CC BY 4.0; BEIR mirror labeled CC BY-SA 4.0. |
| HotpotQA | Yang et al. (2018), [original repository](https://github.com/hotpotqa/hotpot) | CC BY-SA 4.0 source dataset; underlying Wikipedia content is excluded. |
| BRIGHT | Su et al. (2025), [dataset card](https://huggingface.co/datasets/xlangai/BRIGHT) | CC BY 4.0 card; benchmark text excluded. |
| BEIR | Thakur et al. (2021), [repository](https://github.com/beir-cellar/beir) | BEIR says its packaging does not grant every upstream dataset right. |

The source campaign, input hashes and original/clean code identities are in `provenance.json`. The computational validation evidence is in `validation/`. No research-project funding award or publisher grant is asserted without evidence. The source FiQA challenge sponsorship above is attributed to FiQA, not to this study.
