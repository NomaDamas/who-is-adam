<h1 align="center">Who is ADAM?: Automated Desk and Academic Manuscript Review Agent</h1>

<p align="center">
  <img src="assets/main-figure.jpeg" alt="Main figure: tweet asking who Adam is in response to an ICML review screenshot">
</p>

`who-is-adam` is an agent plugin for reviewing local ICML-style paper PDFs with evidence-grounded checks and Markdown review output.

## Install

Requires Python 3.11+ in the environment where the agent runs commands.

### Codex

```bash
git clone https://github.com/NomaDamas/who-is-adam.git
cd who-is-adam
codex plugin marketplace add .
codex plugin add who-is-adam --marketplace who-is-adam
python3.11 -m pip install -e .
```

### Claude Code

```bash
git clone https://github.com/NomaDamas/who-is-adam.git
cd who-is-adam
claude plugin marketplace add ./
claude plugin install who-is-adam
python3.11 -m pip install -e .
```

## Use

In Codex or Claude Code:

```text
Use the who-is-adam plugin to review /path/to/paper.pdf.
```

The plugin uses the bundled agent skill at `skills/who-is-adam/` and calls the local `who-is-adam review` CLI. Current review generation is the offline/fake-provider path for deterministic contract checks; hosted production LLM review is not wired yet.

## More Docs

- [Operator guide](docs/operator-guide.md)
- [Skill guide](docs/skill-guide.md)
- [Evidence policy](docs/evidence-policy.md)
