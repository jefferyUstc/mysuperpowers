# Measuring the routing

Routing is a hypothesis about your tasks, not a guaranteed saving. Measure before claiming anything.

## Arms

Same task, same repo, same prompt, a fresh session each run.

1. Routing off: `scripts/install.sh --uninstall` (children inherit the session model).
2. Routing on: `scripts/install.sh`.

Switch to one arm, open a new session, run, record; switch to the other, repeat. `n = 1` for a coding task; `n = 3` for a cheap repeatable one such as a fixed read-only scan question.

## Record per run

- `/usage` → *Usage by model*: input, output, cache read, cache write, and the `$` figure per model.
- Spawn count and each child's model (`/tasks`, or `verify.sh --transcript`).
- Outcome: did the task finish to the same bar (tests pass, review clean)?

Decide before the run whether delegation is expected (`yes` / `no` / `either`). Zero spawns on an `either` task is fine; zero on a `yes` task is a routing miss; spawns on a `no` task are over-delegation.

## Reading the numbers

- Expected shape: more total tokens, fewer dollars.
- A cheaper run that needed another turn to fix the child's work is not cheaper.
- Plan quota is not API spend. On Pro / Max the `$` is a list-price estimate, but the per-model split still shows which model burned the tokens, and Opus-specific limits exist apart from the shared session and weekly windows.
- Say "on this task, in this repo, n = N". Never "cheapest".

## List prices

USD per 1M tokens, Anthropic API, as cached on 2026-06-24. Confirm on the Console price page before publishing; if your org sets `modelPricing`, `/usage` already reports at contracted rates.

| Alias | Model | Input | Output |
|---|---|---|---|
| `fable` | `claude-fable-5-1` | 10.00 | 50.00 |
| `opus` | `claude-opus-5` | 5.00 | 25.00 |
| `sonnet` | `claude-sonnet-5` | 2.00 | 10.00 |

Thinking tokens bill as output: a worker at `effort: xhigh` can cost several times one at `low` on the same brief. Effort is a lever, not a free setting.
