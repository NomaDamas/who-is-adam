# who-is-adam

English is the default project documentation. Current English docs: [product proposal](docs/product-proposal.md), [operator guide](docs/operator-guide.md), [evidence policy](docs/evidence-policy.md), [implementation checkpoints](docs/implementation-checkpoints.md), and [skill guide](docs/skill-guide.md). Korean translations are available under `docs/ko/`, starting with [docs/ko/README.md](docs/ko/README.md).

## Product proposal summary

`who-is-adam` is an ICML 2026 Main Track PDF review assistant. The project started as a docs-first proposal and now includes implemented checkpoints for an offline/fake-provider CLI, PDF structure extraction, safety gates, ICML desk checks, external evidence clients, specialist/synthesis review generation, and Markdown output persistence. Hosted LLM clients and production review-quality guarantees are not claimed as complete yet. The tool reads one local PDF, checks it against ICML 2026 Main Track submission limits and review-form constraints, separates paper-internal evidence from external metadata, and saves an evidence-grounded Markdown review draft.

Core goals:

- Extract title, abstract, body sections, tables, figures, equations, references, and page-level evidence from a PDF.
- Safely refuse low-quality scans, damaged or encrypted PDFs, and suspected prompt-injection inputs.
- Check ICML 2026 Main Track constraints for a single PDF, maximum 50 MB file size, 8-page main-body limit, anonymity, and LaTeX-format-related signals.
- Use Crossref, Semantic Scholar, arXiv, and public OpenReview evidence without inventing unverified facts.
- Synthesize independent specialist-review perspectives into Markdown that follows the official ICML Main Track fields and score ranges.

## Why this tool is needed

Reviewers need to reason about paper quality, policy compliance, citation accuracy, and safe LLM usage at the same time. This tool does not replace reviewer judgment; it reduces repetitive evidence collection and formatting work. The design treats both PDF contents and external API responses as untrusted inputs so that instructions embedded in a paper, or errors in outside metadata, cannot override the review policy.

## Installation

Clone the repository and install the package in a Python 3.11+ virtual environment:

```bash
git clone https://github.com/kwon/who-is-adam.git
cd who-is-adam
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .
```

Optional OCR support requires the Python extra and the Tesseract system package:

```bash
python -m pip install -e '.[ocr]'
```

On macOS, install Tesseract with Homebrew:

```bash
brew install tesseract
```

On Debian/Ubuntu Linux, install Tesseract with apt:

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

Verify the installed CLI is visible:

```bash
who-is-adam --help
who-is-adam review --help
```

## Quick start CLI

The offline/fake-provider CLI path is implemented and can save contract-test review drafts without network access or real API keys.

```bash
who-is-adam review paper.pdf --output-dir reviews --llm-policy "<assigned policy>" --code-of-conduct-ack --offline
```

Arguments:

- `paper.pdf`: one local ICML 2026 Main Track PDF.
- `--output-dir`: root directory for saved review Markdown and diagnostics.
- `--llm-policy`: the assigned ICML LLM-use policy name or text. Required.
- `--code-of-conduct-ack`: explicit acknowledgement that the ICML code of conduct was checked and recorded in runtime metadata. Required.
- `--offline`: run with the fake LLM and record external provider evidence as `unavailable` for test/offline mode.

## Usage

Run the currently implemented offline path with a local PDF. The fake LLM produces deterministic contract-test output; it is useful for integration checks, not for real paper-quality review.

```bash
WHO_IS_ADAM_OFFLINE=true who-is-adam review paper.pdf \
  --output-dir reviews \
  --llm-policy "ICML assigned LLM policy checked" \
  --code-of-conduct-ack \
  --offline
```

A successful run exits with code `0` and writes a versioned Markdown file such as:

```text
reviews/a_study_of_adam/a_study_of_adam_review_1.md
```

A safe refusal exits with code `2`, prints diagnostics, and does not write review Markdown. For example, a non-PDF input is refused before review generation:

```bash
who-is-adam review notes.txt --output-dir reviews --llm-policy "ICML assigned LLM policy checked" --code-of-conduct-ack --offline
```

Missing required runtime acknowledgements are CLI usage errors, for example:

```bash
who-is-adam review paper.pdf --output-dir reviews --offline
```

Hosted production review is not wired in this checkpoint. Offline fake reviews are contract tests for the implemented pipeline and must not be described as production-quality ICML reviews.
Hosted LLM provider settings exist in the configuration schema, but hosted LLM clients are not wired in the current checkpoint. Do not treat the hosted-provider path as a documented production review path yet.

## Scope and limits

Scope is limited to ICML 2026 Main Track PDF review assistance. Documented official limits and reviewer obligations are:

- A submission must be a single PDF and at most 50 MB.
- The main body may be up to 8 pages; references and appendices may follow the main body.
- Submissions must be anonymized; LaTeX format requirements and page/format violations may be automatic desk-reject reasons.
- Reviewers must follow the assigned LLM policy, confidentiality requirements, professional and constructive conduct expectations, and code-of-conduct acknowledgement.
- Official Main Track review score ranges are Soundness/Presentation/Contribution 1-4, Rating 1-6, and Confidence 1-5.

Out of scope:

- Position Track reviews.
- Actual submission to OpenReview or ICML systems.
- Editing, rewriting, or acting on behalf of paper authors.
- Generating historical OpenReview strengths or weaknesses without public evidence.
- Guaranteeing OCR success for every scanned PDF.
- Operational review generation through hosted LLM providers in the current checkpoint.

## Safe refusal policy

The tool is designed to refuse inputs that cannot support a trustworthy review before generating the official review Markdown. In these cases it should not save a review Markdown file; it should return operator-readable diagnostics instead:

- The input is not a PDF, is missing, exceeds 50 MB, or is damaged/encrypted so that structure extraction cannot proceed.
- Text density or OCR confidence is too low to read the paper reliably.
- The PDF contains prompt-injection signals such as instructions to ignore reviewer/system instructions, manipulate scores, or change tool policy.
- The configured LLM provider does not support constrained JSON-schema output, required model/API-key settings are missing, or valid JSON cannot be produced after retries.

A safe refusal is not a paper-quality judgment. It means the input or runtime environment does not permit reliable review generation.

## Evidence policy

Every judgment must distinguish its evidence source:

- PDF-internal evidence: record page, section, and quoted text span.
- External metadata: use Crossref, Semantic Scholar, and arXiv only as reference fact-checking aids.
- OpenReview: use prior public strengths, weaknesses, or comparison evidence only when public OpenReview evidence exists.
- No evidence: leave API absence, rate limits, search failures, and lack of public evidence as `unavailable`; do not invent claims.

PDF body text, references, and external review text are all outside the trust boundary. They cannot change review instructions or override system rules.

## Output location and file names

A successful review is saved as versioned Markdown under a directory derived from the normalized paper title:

```text
<output-dir>/<normalized_title>/<normalized_title>_review_{n}.md
```

`normalized_title` is a filesystem-safe name produced by the internal slug/path sanitizer. `n` is one greater than the largest existing review number in the same directory. For example, if `reviews/a_study_of_adam/a_study_of_adam_review_3.md` exists, the next saved file is `a_study_of_adam_review_4.md`. Collision handling must avoid overwriting previous results by using atomic writes and recomputing the review number.

## Environment variables and provider summary

Runtime environment variables, fake/offline mode, and provider-specific failure semantics are documented in the English [operator guide](docs/operator-guide.md). The main providers are LLM, OpenReview, Semantic Scholar, Crossref, arXiv, and optional OCR/Tesseract.

## Development and verification checkpoints

Step-by-step file scope, verification commands, expected behavior, and commit messages are documented in the English [implementation checkpoints](docs/implementation-checkpoints.md). The project has progressed beyond the original docs-only checkpoint: product code and tests now exist for the offline CLI/review path.
