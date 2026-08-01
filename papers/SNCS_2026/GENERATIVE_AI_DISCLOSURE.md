# Generative-AI Disclosure (Stage 5)

## Placement decision

Per `POLICY_CHECK.md` Section 1, Springer Nature requires generative-AI
disclosure inside the manuscript's Methods section (or, where no Methods
section exists, "a suitable alternative part"), **not** as a separate
Declarations heading. This manuscript's closest equivalent to Methods is
`\subsection{Reproducibility and Implementation}`
(`sec:reproducibility`, the last subsection of Methodology). The
disclosure text below has been inserted there, as its final paragraph,
since policy verification supports that placement directly. It is not
duplicated in the Declarations backmatter, consistent with the policy
finding that AI disclosure is not a Declarations-list item.

## Disclosure text (as inserted in `main.tex`)

> Generative artificial-intelligence tools (Anthropic's Claude, via the
> Claude Code command-line environment) were used to assist with software
> development for this study -- writing and revising analysis code,
> statistical-inference utilities, figure-generation scripts, and audit
> scripts -- and with drafting, revising, and fact-checking portions of
> this manuscript's text and figures. Every AI-assisted code change,
> statistical analysis, figure, table, citation, and passage of
> manuscript text was reviewed and independently verified against the
> underlying stored data and source code by the author before inclusion;
> no generative-AI output was accepted without that verification. The
> author takes full responsibility for the accuracy, integrity, and
> originality of the source code, experiments, statistical analyses,
> figures, tables, interpretations, citations, and manuscript text in
> this work. No generative-AI tool is credited as an author, and no
> generative-AI tool independently designed the study, selected the
> research questions, or made scientific judgments attributed to the
> author in this manuscript.

This wording deliberately: (a) names the type of use (software
development assistance and manuscript drafting/editing assistance,
per the task brief's two required categories) without implying AI
authorship; (b) states author review and validation of all generated
content; (c) states the author's full responsibility across every
listed output category the task brief requires (source code,
experiments, statistical analyses, figures/tables, interpretations,
citations, manuscript text); (d) states no output was accepted without
verification; (e) explicitly denies that the tool made scientific design
decisions, addressing Springer Nature's stated rationale for prohibiting
AI authorship (accountability cannot attach to an LLM).

## Tool-naming

`POLICY_CHECK.md` confirms Springer Nature does not require naming the
specific tool or version. This disclosure names the tool family
("Claude," "Claude Code") as a transparency choice beyond the minimum.

The exact model differed across drafting and audit stages depending on
session configuration, and the available record does not support a
complete per-stage model breakdown. The manuscript therefore stays at the
tool-family level ("Claude") to avoid asserting a specific model identity
that cannot be verified for every stage.

## Software-development AI assistance: same disclosure, not a separate one

Per `POLICY_CHECK.md` Section 1's flagged policy gap (Springer Nature's
Code Policy does not address AI-assisted code separately), this
manuscript discloses AI-assisted code development under the same general
statement as manuscript-text assistance, in the same Methods-equivalent
location, rather than creating a second disclosure elsewhere. This is a
deliberate choice toward more disclosure, not less, given the ambiguity.

## What this disclosure is not

It does not claim, and must not be edited to claim, that: the AI tool is
a co-author or contributor in the authorship sense; the AI tool
independently produced the study's research questions, experimental
design, or conclusions; any generated content was used without
verification; or that AI assistance excuses the author from
responsibility for any part of the work. `POLICY_CHECK.md` Section 1's
exact authorship-prohibition wording is the standard this statement is
held to.
