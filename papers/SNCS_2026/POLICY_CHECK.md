# Policy Check: Springer Nature / SN Computer Science Declarations and AI Disclosure (Stage 5)

Verified against official Springer Nature sources during Stage 5
(2026-07-31), not secondary summaries. This supersedes/extends the
declarations research already done in Stage 3 (`README.md`,
"Compilation" section references; the Declarations backmatter itself was
completed in Stage 3) with a specific focus on generative-AI disclosure,
which Stage 3 did not investigate.

## 1. Generative-AI / LLM use disclosure

**This is a Springer-Nature-group-wide policy, not an SN Computer
Science-specific one** -- confirmed independently across the Nature
Portfolio editorial-policies AI page, the Springer brand's group-wide
journal-policies page, and the SN Computer Science submission-guidelines
page itself (which incorporates the same language under its authorship
instructions).

- **AI cannot be an author.** Exact policy wording: "Large Language
  Models (LLMs), such as ChatGPT, do not currently satisfy our authorship
  criteria," because "an attribution of authorship carries with it
  accountability for the work, which cannot be effectively applied to
  LLMs."
- **Disclosure is required when an LLM/AI tool contributed to the
  research methodology or content** (not just polish). Required
  placement: "in the Methods section (and if a Methods section is not
  available, in a suitable alternative part) of the manuscript" -- a
  related group-level guidance page also names the Introduction, Preface,
  or Acknowledgements as acceptable alternative placements when a
  dedicated Methods section is not the natural fit.
- **AI-assisted copy editing is explicitly exempt from disclosure**:
  "AI-assisted improvements to human-generated texts for readability and
  style, and to ensure that texts are free of errors in grammar,
  spelling, punctuation and tone, including wording and formatting
  changes but not generative editorial work and autonomous content
  creation."
- **No dedicated "Declaration of Generative AI use" heading exists in the
  Springer Nature Declarations framework** (unlike, e.g., Elsevier's
  named declaration block). AI disclosure belongs inside the narrative
  text (Methods or an equivalent section), not the backmatter
  Declarations list.
- **No requirement to name the specific tool and version.** Every
  official page checked requires only that use be documented/disclosed;
  none mandate naming the model or its version, and none provide a
  mandatory template sentence. (An "Elsevier-style" template sentence
  surfaces repeatedly in general web search results for "AI disclosure
  statement" -- that template belongs to a different publisher and must
  not be used here.)
- **AI-assisted code/software development is not explicitly addressed**
  by Springer Nature's dedicated Code Policy or its Software and Code
  Sharing support article -- both are silent on AI. This is a genuine gap
  in the official documentation, not a confirmed answer either way. This
  project's choice, out of caution and transparency: treat AI-assisted
  code development as covered by the same general Methods-section
  disclosure requirement that applies to AI-assisted content generation,
  since the underlying rationale (accountability for what the AI touched)
  applies equally to code and to prose.

Sources: `nature.com/nature-portfolio/editorial-policies/ai`;
`link.springer.com/brands/springer/journal-policies`;
`group.springernature.com/gp/group/ai/ai-guidance-for-our-researchers-and-communities`;
`link.springer.com/journal/42979/submission-guidelines`;
`springernature.com/gp/open-science/code-policy`;
`support.springernature.com/en/support/solutions/articles/6000237619-software-and-code-sharing`.

## 2. Declarations list, order, and where AI disclosure fits

Re-confirmed order under "Statements and Declarations" (placed before the
reference list): **Funding -> Competing interests -> Ethics approval ->
Consent to participate -> Consent to publish -> Data, Material and/or
Code availability -> Authors' contributions.**

**Reconciliation with Stage 3's backmatter**: Stage 3 already used a
single combined heading, "Data, materials, and code availability" (not
two separate "Availability of data and materials" / "Code availability"
headings) -- this Stage-5 research confirms that combined-heading form is
correct and matches the SN Computer Science guidelines page's own
wording ("Data, Material and/or Code availability") almost verbatim. No
change needed to that heading. The manuscript's existing "Conflict of
interest" heading (Stage 1/3) vs. the guidelines page's "Competing
interests" wording is a synonym Springer Nature itself uses
interchangeably across templates (confirmed both terms appear on
official pages); left as "Conflict of interest" since that is the
heading already present and both are accepted.

**Generative AI disclosure is not a Declarations-list item.** It does not
get its own heading in the backmatter; it belongs in Methods (or
Reproducibility, as this manuscript's closest equivalent) or, failing
that, an Acknowledgements-style note. See
`GENERATIVE_AI_DISCLOSURE.md` for the placement decision this manuscript
makes.

## 3. Authors' contributions

**CRediT is recommended, not mandatory.** Exact guidance: "the Publisher
recommends authors to include contribution statements in the work that
specifies the contribution of every author." Both a free-text narrative
form and a CRediT-role-labeled form are shown as acceptable examples. For
a single-author manuscript, a short narrative statement naming the roles
fulfilled (already present in the Stage-3 backmatter) satisfies this;
CRediT-style role labels are optional polish, not a requirement, and are
not added here since the existing narrative statement is already
sufficient per this confirmed guidance.

Source: `link.springer.com/journal/42979/submission-guidelines`.

## 4. Items already verified in Stage 3 (not re-litigated here)

Article type (Original Research), absence of a page/word/figure-count
limit beyond the 150-250-word structured abstract, three-heading-level
maximum, and the full mandatory-even-if-"Not applicable" declarations
requirement were all verified in Stage 3
(`README.md`, "Stage-2 resolutions" and page-budget sections) and remain
current; not re-verified this stage since nothing in this stage's task
brief suggested they might have changed.

## 5. Not found / explicitly unconfirmed

- No Springer Nature source explicitly separates an "AI wrote my code"
  policy from an "AI wrote my prose" policy -- flagged, not guessed
  around (see Section 1).
- No mandatory AI-tool-naming requirement found (see Section 1) --
  this manuscript names the tool anyway, as a transparency choice beyond
  the minimum, not because it is required.
