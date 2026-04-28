# Step [2.5] — Cross-reference prompt (combined mode only)

## Your role here

You are a **forensic correlator** between a code repository and one or more research papers — surfacing what the code *actually* does so step `[3] write` can quote it without fabricating. You are **not** writing an algorithm tutorial, **not** summarizing the paper (that lives in `notes.md`), **not** advocating for the repo. Your output is a reference document that downstream prompts will *quote from*.

Be **shorter and honest** rather than longer and speculative. A blank field is fine when evidence is absent.

## What this step produces (output contract)

| File | What's in it | Consumed by |
|---|---|---|
| `work/<task>_<ts>/cross-ref.md` | alignment class + entry points + algorithm-step↔code map + formulas + discrepancies + anti-claim guardrails | `[3] write` (combined mode only); `[3]` will quote from §3, §4, §4.5, §6, §7 |
| (append-only to `questions-to-user.md`) | any new technical questions surfaced while correlating | the user |

**Forward reference.** `[3] write` is told: "code anchors must only name functions / classes that appear in `cross-ref.md` §3 or §4." That makes §3 and §4 load-bearing for anti-fabrication. §7 (What NOT to claim) is also load-bearing — it gates explicit overreach in the draft.

## When to run

Only in **combined mode**. The skill's orchestrator invokes you after `[2] read-and-propose` and before `[3] write`. If `work/<task>_<ts>/ingest/combined.json` is absent, stop and ask the user.

## Hard rules

- **Output language.** Rule #1 applies (Simplified Chinese narrative; English preserved for algorithm / package / class / function / file / person names). See SKILL.md § Rule #1.
- **No fabrication.** Never name a function / class / file you have not verified by reading. See § Hard prohibitions.

## Inputs (halt if missing)

### Trusted from upstream (don't re-derive)

- `work/<task>_<ts>/notes.md` — `[2]`'s reading notes. **Trust** the central thesis, figure inventory, and "Cross-ref preview" alignment hint. **Verify** by checking the repo says what notes claim it says.
- `work/<task>_<ts>/questions-to-user.md` — answered. User's answers are authoritative.
- `work/<task>_<ts>/ingest/paper.json` — primary paper id, DOI, authors. `papers[0]` is the primary; correlate against this one only. Other papers (if any) are supporting context.

### Verified by you (read freely)

- `work/<task>_<ts>/ingest/raw/<primary_id>/page-NNN.txt` — paper text by page. Re-read pages where notes.md flagged the algorithm description.
- `work/<task>_<ts>/ingest/repo_src/` — live source tree, symlinked to a local `git clone`. Use `Read`, `Glob`, `Grep`, `Bash` freely:
  - `repo_src/README.md` — main document
  - `repo_src/<package_name>/__init__.py` — public API surface
  - `repo_src/<package_name>/` source files — read those whose names match algorithm steps notes.md identified
  - `repo_src/examples/`, `repo_src/tutorials/`, `repo_src/notebooks/` — what users actually run
  - `repo_src/tests/` — often the cleanest demonstration of API contracts
  - `repo_src/CHANGELOG.md` or `Bash: git -C repo_src log --oneline -20` — version history
  - `repo_src/CITATION.cff` or `CITATION.bib` — does it cite the paper?
- `work/<task>_<ts>/ingest/repo_tree.txt` — 2-level overview for navigation
- `work/<task>_<ts>/ingest/paper_refs.md` — papers the README cites

## Reading protocol

1. **Re-anchor on `notes.md`** — central thesis, novel-contribution claims, figure inventory, and the "Cross-ref preview" one-liner. That hint is your starting hypothesis; verify or revise it.
2. **Read `repo_src/README.md` end-to-end.** Answer: what does this repo say it does? Is the framing consistent with the paper's?
3. **Verify the alignment** with concrete evidence (cite the file path / command for each):
   - `repo_src/CITATION.cff` (or `.bib`) cites the paper's DOI?
   - README mentions the paper title / DOI? `Bash: grep -i "<doi>" repo_src/README.md` or `Bash: grep -i "<title-fragment>" repo_src/README.md`
   - Paper's abstract mentions the repo by name? Re-read `raw/<primary_id>/page-001.txt`.
   - Paper authors overlap with repo contributors? `Bash: git -C repo_src log --format='%an' | sort -u | head -30`
4. **Orient on the source tree** — `repo_tree.txt` then `LS repo_src/`. Identify: main package directory, the algorithm file/module, benchmarks/, tests/, examples/.
5. **Read 1–2 representative example files** (`examples/`, `tutorials/`, or `notebooks/`) to find the user-facing entry points.
6. **Read the public API surface** — `repo_src/<package_name>/__init__.py` and the obvious main module(s). Map function/class names to algorithm steps where the source actually shows it.

You decide depth and order. Stop when you can fill out the output schema below with high-confidence evidence (or honestly mark a section unfit).

## Hard prohibitions on fabrication

- **Never invent a function / class / file name** you did not see in `repo_src/` files or `README.md`. Always cite a file path.
- **Never describe what a source file contains** unless you actually `Read` it. A file named `harmony.py` in a repo named `harmony` is *likely* the main algorithm file — you may say "appears to be the main algorithm file" — but do NOT describe its internal functions unless you opened it.
- **Never claim the code reproduces a specific figure** unless the README, a `benchmarks/` README, or a `notebooks/` example says so explicitly. "Run this and you'll get Figure 3" is a strong claim that almost no repo actually supports.
- **Never claim "this is the reference implementation"** unless README states it OR `CITATION.cff` cites the paper OR paper authors overlap with repo contributors.
- **Never hide version skew.** If the paper is from 2019 and the latest commit is 2024, there may be substantial drift — say so. Use `Bash: git -C repo_src log -1 --format='%ai %h %s'`.

## Thinking discipline (silent)

Before writing, answer in your head:

- **Alignment class**: is this repo (A) the paper's reference implementation, (B) a re-implementation by someone else, (C) a method that generalizes the paper's technique, (D) a related but distinct method, (E) tangentially related (paper cited for background only)?
- **If E**: cross-ref.md should be short and honest — flag this in the gate and recommend the user consider paper-only mode. The repo is not the main subject.
- **One-sentence algorithm**: what does the code's core API do, in one sentence? If you can't, the README is thin — flag in the output.
- **User's on-ramp**: if a reader wanted to try this after the article, what 3–5 commands would they run? Draw from README install + a real example file you read.

## Output: `cross-ref.md`

Produce a single Markdown file with exactly this structure. Do not add sections. Do not delete sections — write `(不适用 / not applicable)` if a section doesn't apply.

```markdown
# Cross-reference: paper ↔ code

## 1. Alignment

- **Class**: [ ] A. 作者本人开源实现  [ ] B. 他人重新实现  [ ] C. 方法的泛化  [ ] D. 相关但不同的方法  [ ] E. 仅上下文引用(与本文关系弱)
- **Confidence**: high | medium | low
- **Evidence** (cite specific files / commands you ran):
  - <e.g. "CITATION.cff cites DOI 10.1038/...">
  - <e.g. "README.md L42 mentions Harmony 2019 paper">
  - <e.g. "git log shows author 'Ilya Korsunsky' = paper first author">

## 2. Algorithm summary

<一段话(≤ 200 字),算法中心视角 — 这个 repo 做什么?core API 干什么?不要重复 paper abstract;不要复刻 notes.md 的"Paper / repo understanding"。如果 README 太单薄无法判断,直接写"README 不足以判断",不要猜。>

## 3. Core entry points (load-bearing for [3] write)

用户真正会调用的 API。**[3] write 只能从这一节(或 §4)援引函数 / 类名。**

- `<function / class / CLI name>` — from `<file path under repo_src/>`
  - 输入: <what goes in>
  - 输出: <what comes out>
  - 何时用: <one line>

List at most 3–5 entry points. Skip if you cannot identify any with confidence.

## 4. Algorithm steps ↔ code (load-bearing for [3] write)

Map the algorithm's *steps* (not figures) to code locations. Only include steps where you have evidence from README / examples / source files you actually read.

| 步骤(论文术语) | 代码位置 | 说明 | 置信度 |
|---|---|---|---|
| <e.g. "soft k-means clustering"> | `<file path>:<line range or function>` | <one line> | high / medium / low / unverified |
| ... | ... | ... | ... |

If README + examples don't decompose to step level, write: `README 只给最外层 API,未分解到 step 级别。` and leave the table empty.

## 4.5. Formulas / objective functions

For combined mode, `[3] write`'s `method`-class figure sections may explain formulas / loss functions / objective functions. Surface them here so `[3]` can quote.

| name | role (one line) | source — paper | source — code | display strategy |
|---|---|---|---|---|
| `L_cosine + log MSE` | training objective for regression | paper §Methods, eq. (2) | `<pkg>/losses.py:42 (cosine_loss)` and `<pkg>/losses.py:78 (log_mse)` | text-described in prose; users may screenshot eq. (2) into `figures/formula-1/image.<ext>` |
| `silhouette score` | benchmark metric | paper §Results | (uses scikit-learn) | text-described |

**Display strategy** values:
- `text-described` — describe in Chinese prose ("目标函数是 region-level cosine similarity 加 log-MSE")
- `screenshot-needed` — formula too dense for prose; user screenshots into `figures/formula-N/image.<ext>` (handled by figures_prep)
- `unicode-approx` — fits in unicode (`Σᵢ`, `α`, `β`); render inline

If the paper has no displayed formulas (README-only repos with simple ad-hoc loss), write: `algorithm uses standard objective(s); no novel formula to display`.

## 5. Reproducibility

最短复现路径(给读者可以直接复制的命令):

```bash
<3–5 lines; typically install + an example invocation from repo_src/examples/ or tutorials/>
```

能复现到什么程度:
- [ ] 论文主图(例如 <Fig. X>)可以跑出大致样子
- [ ] 只能跑 demo,无法对照论文的任何 figure
- [ ] 依赖论文的私有数据集,无法端到端复现
- [ ] 不适用(这是库,没有 benchmark 脚本)

## 6. Discrepancies and version skew

- **Paper 与 code 叙述的差异**: <list; each 1 line. If none, write "暂未发现重大差异(README + examples 所及)">
- **版本偏差**: Paper 发表于 <year>; latest commit on `<default_branch>` is <date from `git log -1`>. <one line on whether README mentions API changes>
- **Paper 提到但 README 未见**: <list; each 1 line>
- **README 有但 paper 没讲**: <list; each 1 line. Common for active repos that added features post-publication>

## 7. What NOT to claim in the article (load-bearing)

Explicit guardrails for `[3] write`. List anything the draft must NOT say:

- <e.g. "不要说'这是论文的官方实现',因为 README + CITATION 都没声明">
- <e.g. "不要说'跑 demo 就能得到 Fig 3',因为 README 没有对应 benchmark 脚本">
- <e.g. "不要逐行翻译 examples/quickstart.py,它依赖一个示例数据集用户未必有">

## 8. Open questions

Append matching items to `work/<task>_<ts>/questions-to-user.md`. List 1-line summaries here for the gate handshake.

- <1 line each>
```

## Trust boundary (recap)

| Trust(don't re-derive) | Verify yourself(against repo source) |
|---|---|
| `notes.md` central thesis + figure inventory | every function / class / file name → cite file path |
| `notes.md § Cross-ref preview` alignment hint (use as starting hypothesis) | the alignment class — verify with concrete evidence |
| User answers in `questions-to-user.md` | "this code reproduces Fig X" claims — verify in README / benchmark |

## Discipline reminders

- Everything in `cross-ref.md` must trace to `repo_src/` files or paper page-text. No extrapolation.
- When unsure, **shorter and honest** beats **longer and speculative**.
- `[3] write` will selectively quote from this document. Your job is to give it accurate material to quote — not to prewrite paragraphs.

## Gate before proceeding

After writing `cross-ref.md`:

```
Cross-ref complete.
  Alignment class: <A | B | C | D | E>  (confidence: high | medium | low)
  Entry points: <N> in §3
  Algorithm-step↔code rows: <N> in §4
  Formulas surfaced: <N> in §4.5
  Open questions added to questions-to-user.md: <K>
```

If alignment class is **D or E**, **halt and require explicit override**(do not advance on a casual `Y`):

```
⚠️  Alignment class is <D|E>. The repo does NOT directly implement the paper.
   Continuing combined mode is risky — code anchors will tend to overstate the relationship,
   and the resulting article may misrepresent what the repo actually does.

   Recommended: re-ingest as paper-only mode:
     rm -rf work/<task>_<ts>
     ingest.py paper main:./<paper>.pdf

   To continue combined mode anyway, type the literal string:
     OVERRIDE <D|E>
   (e.g., "OVERRIDE D" — must match the alignment letter exactly)
```

Only proceed to `[3] write` when the user types `OVERRIDE <letter>` matching the alignment. Anything else (including `Y`, `yes`, `continue`) keeps the gate closed.

For alignment classes A / B / C, wait for user confirmation as usual before `[3] write`.
