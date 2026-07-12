# Citation Verification Contract

Use this procedure before making novelty, attribution, or prior-work judgments.

## Procedure

1. Parse each reference into title, authors, year, venue, volume, issue, pages, publisher, DOI,
   and arXiv ID. Preserve the raw reference and mark fields that could not be parsed.
2. Query public Crossref, Semantic Scholar, and OpenAlex metadata. Query arXiv when an arXiv ID is
   present. Consider up to five search candidates and retain the candidate with the highest title
   similarity; do not assume the first result is correct.
3. Normalize LaTeX accents, braces, punctuation, whitespace, DOI URLs, page dashes, venue names,
   and author names before comparison.
4. Require all available identity evidence to agree:
   - title similarity of at least 85%;
   - exact year when both sides provide a year;
   - at least 30% author surname overlap when both sides provide authors;
   - exact DOI and arXiv ID agreement when both sides provide them;
   - compatible venue and publisher metadata when both sides provide it;
   - exact normalized volume, issue, and page-range agreement when both sides provide it.
5. Cross-check verified provider records against each other using the same title, year, and author
   surname overlap rules. Preserve every provider conflict.
6. Detect exact duplicate references by normalized DOI, arXiv ID, or title plus year.

## Statuses

- `verified`: title and at least one independent metadata field agree, with no conflicts.
- `weak_match`: title agrees but independent metadata is insufficient.
- `needs_review`: title is borderline, an identifier resolves to a conflicting title, a compared
  field differs, or providers disagree.
- `not_found`: no candidate reaches the minimum title similarity and no identifier resolved.
- `metadata_error`: a provider response is malformed or lacks required title metadata.
- `unavailable`: retrieval could not be performed because tools, network, or provider access were
  unavailable.

Do not auto-correct the submitted manuscript. Report the original value, matched value, similarity
or equality result, provider URL, duplicate index, and uncertainty in `Evidence and Provenance`.
Citation status informs reviewer confidence; it must not mechanically determine paper scores.
