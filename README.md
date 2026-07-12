<h1 align="center">Who is ADAM?: Automated Desk and Academic Manuscript Review Agent</h1>

<p align="center">
  <img src="assets/main-figure.jpeg" alt="Main figure: tweet asking who Adam is in response to an ICML review screenshot">
</p>

`who-is-adam` is an agent skill for reviewing local ICML-style paper PDFs with evidence-grounded checks and Markdown review output.

## Use as a Skill

Install the package in the environment where your coding agent runs commands:

```bash
git clone https://github.com/NomaDamas/who-is-adam.git
cd who-is-adam
python -m pip install -e .
```

Then make the bundled skill available to your agent by copying `skills/who-is-adam/` into your skill directory, for example:

```bash
cp -R skills/who-is-adam ~/.gjc/skills/
cp -R skills/who-is-adam ~/.claude/skills/
```

Invoke it with a slash skill if your agent supports that:

```text
/skill:who-is-adam /path/to/paper.pdf
```

Or use a natural-language prompt:

```text
Use the who-is-adam skill to review /path/to/paper.pdf.
```

The skill wrapper calls the local `who-is-adam review` CLI. The current supported runtime path is offline/fake-provider review generation for deterministic contract checks; hosted production LLM review generation is not wired yet.

## Workflow

1. The skill receives a local paper PDF path and required reviewer acknowledgements.
2. The CLI extracts paper structure: title, abstract, sections, pages, references, figures, tables, and extraction metrics.
3. Safety gates reject unreadable PDFs, low-quality extraction, or prompt-injection attempts before review generation.
4. ICML desk checks reject blocking format, anonymity, scope, or page-limit issues.
5. Independent specialist reviewer lenses assess methodology, evidence, novelty, presentation, ethics, and reproducibility.
6. A synthesis step merges the specialist outputs into the official review fields: summary, strengths/weaknesses, questions, limitations, scores, confidence, evidence, consensus, conflicts, and minority opinions.
7. Citation and OpenReview lookups attach only public evidence when available; missing external evidence stays unavailable rather than being guessed.
8. The Markdown review is saved under a versioned path such as `reviews/<paper-title>/<paper-title>_review_1.md`.

## More Docs

- [Operator guide](docs/operator-guide.md)
- [Skill guide](docs/skill-guide.md)
- [Evidence policy](docs/evidence-policy.md)
