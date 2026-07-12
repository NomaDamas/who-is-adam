<h1 align="center">Who is ADAM?: Automated Desk and Academic Manuscript Review Agent</h1>

<p align="center">
  <img src="assets/main-figure.jpeg" alt="Main figure: tweet asking who Adam is in response to an ICML review screenshot">
</p>

`who-is-adam` is an agent plugin and CLI for reviewing local ICML-style paper PDFs with evidence-grounded checks and Markdown review output.

Korean translation: [docs/ko/README.md](docs/ko/README.md)

## Product proposal summary

The supported target is an ICML 2026 Main Track review draft. The agent accepts one local PDF, extracts structure and references, checks safety and desk-reject conditions, runs independent reviewer lenses, synthesizes official ICML review fields, attaches available citation/OpenReview metadata, and writes a versioned Markdown artifact for a human reviewer to inspect.

Current status: the offline/fake-provider CLI path is implemented for deterministic contract checks. Hosted LLM clients and production review-quality guarantees are not claimed as complete yet. In offline mode the fake LLM is used, and external evidence is recorded as `unavailable` instead of being replaced by fixture-backed provider claims.

## Workflow

1. The user invokes `who-is-adam review` directly or asks an agent to use the bundled skill.
2. The CLI validates runtime acknowledgements, file type, and the 50 MB input limit.
3. PDF extraction builds title, abstract, sections, pages, references, and extraction metrics.
4. Safety gates reject unreadable text, OCR-poor inputs, and prompt-injection attempts before review generation.
5. ICML desk checks enforce the ICML 2026 Main Track contract, including the 8-page main-body limit and anonymity/scope checks.
6. Specialist reviews are generated independently, then synthesized into Summary, Strengths And Weaknesses, Questions, Limitations, Soundness/Presentation/Contribution 1-4, Rating 1-6, and Confidence 1-5.
7. Citation and OpenReview lookups attach only public metadata or public review strength/weakness fields when available.
8. The final Markdown is written under a versioned output path and never submitted automatically.

## Safe refusal policy

The tool refuses before writing review Markdown when the input is not a PDF, exceeds 50 MB, cannot be extracted safely, appears prompt-injected, or fails blocking ICML Main Track desk checks. Exit code `2` means safe refusal; exit code `0` means review Markdown was saved.

## Evidence policy

PDF text, references, captions, metadata, and retrieved provider responses are treated as untrusted evidence. OpenReview evidence limits are strict: absent, private, weak, or rate-limited evidence stays `unavailable`; the tool does not invent public review history, strengths, weaknesses, or prior-work judgments.

## Output location and file names

Saved reviews are versioned by normalized title:

```text
reviews/a_study_of_adam/a_study_of_adam_review_1.md
reviews/a_study_of_adam/a_study_of_adam_review_2.md
```

Existing review files are not overwritten.

## Installation

Requires Python 3.11+ in the environment where the agent runs commands.

```bash
git clone https://github.com/NomaDamas/who-is-adam.git
cd who-is-adam
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

Optional OCR support requires the Python extra plus Tesseract:

```bash
python -m pip install -e '.[ocr]'
brew install tesseract
sudo apt-get install tesseract-ocr
```

## Usage

Check the CLI surface:

```bash
who-is-adam review --help
```

Run the current deterministic offline path:

```bash
WHO_IS_ADAM_OFFLINE=true who-is-adam review paper.pdf \
  --output-dir reviews \
  --llm-policy "assigned ICML reviewer policy" \
  --code-of-conduct-ack
```

Bad inputs are refused, for example:

```bash
who-is-adam review notes.txt
```

You can also ask an agent in natural-language:

```text
Use the who-is-adam plugin to review /path/to/paper.pdf.
```

## Install as an Agent Skill

The default GJC workflow uses the skill package at `skills/who-is-adam/`; its runtime contract is defined in `skills/who-is-adam/SKILL.md`. Install the Python CLI first with `python -m pip install -e .`, then copy the skill package into the agent skill directory you use:

```bash
cp -R skills/who-is-adam .gjc/skills/
cp -R skills/who-is-adam ~/.gjc/skills/
cp -R skills/who-is-adam .claude/skills/
cp -R skills/who-is-adam ~/.claude/skills/
```

When slash skills are available:

```text
/skill:who-is-adam /path/to/paper.pdf
```

When slash skills are unavailable, use a natural-language prompt. The SKILL.md wrapper still routes to the local `who-is-adam review` CLI and preserves the same offline/fake and `unavailable` external-evidence semantics.

## More Docs

- [Operator guide](docs/operator-guide.md)
- [Skill guide](docs/skill-guide.md)
- [Evidence policy](docs/evidence-policy.md)
- [Product proposal](docs/product-proposal.md)
- [Implementation checkpoints](docs/implementation-checkpoints.md)
