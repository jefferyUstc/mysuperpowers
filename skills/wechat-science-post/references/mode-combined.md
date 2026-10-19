# Combined mode: paper + repository

The article is still a paper interpretation: figures drive the structure. The repository adds depth where the paper's method is explained, and it adds risk, because it is easy to name code that does not exist or to claim the code does more than it does.

## Truth order

1. Source files you have opened in `ingest/repo_src/` — the only basis for any statement about what the code does.
2. Notebooks and examples — how the API is used, not how it works inside.
3. README — the project's self-description; quote it only as "README 中称……".

## Reading (adds to `prompts/read.md`)

Add a section **论文与代码对应** to `notes.md`:

- **Relationship**, with evidence (CITATION file, README naming the paper, shared authors in `git log`, the paper's code-availability statement): A the authors' own implementation; B someone else's reimplementation; C a generalization; D related but different; E only background. For D or E, ask the user whether to keep a code connection at all or write a paper-only article.
- **Entry points** — the functions or classes a user calls, each with the file you read it in.
- **Steps ↔ code** — method steps mapped to file and function, only where you read the source. Leave a step unmapped rather than guessing.
- **Formulas** — the objective or score functions the article might explain, with paper page and code location.
- **不能说的** — claims the article must not make (e.g. "official implementation" without evidence, "reproduces Fig 3" without a script that does).
- **Version** — paper year against `repo.last_commit` in the manifest; note drift.

## Writing (adds to `prompts/write.md`)

- Method sections may carry a code anchor: the function name and file path, at most a few lines, taken only from **论文与代码对应**. No runnable tutorial blocks; reader runnability is not the goal here.
- The combined budget is larger (lint range 3,000–12,000) only because method sections carry this extra layer; other sections stay paper-sized.
- Attribution line includes `代码: <repo url>`.
