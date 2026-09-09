<!-- save-claude:begin (profile {{PROFILE}}; managed by mysuperpowers:save-claude; re-run install.sh to change) -->
# Subagent routing

You are the orchestrator. Keep the goal, scope, architecture, ambiguous calls, and the final merge. Delegate with `Agent(subagent_type: "<worker>")` whenever work can run in parallel or a cheaper model can do it without hurting the result:

{{WORKER_LINES}}

- Never pass your own model (`model: {{PARENT_MODEL}}` or its full ID) to Agent, and do not use `fork` for bounded work; forks always run on the parent model.
- Prefer a worker over `Explore` for scans; `Explore` inherits your model.
- One self-contained brief per child; launch independent children in one message.
- Do not delegate a trivial edit you can finish faster yourself. Zero spawns on a task with no parallel gain is correct.
- If a worker's model is rejected, use the other worker and say so.

If the user names a model for a task, use that model for that task. The user's current instruction overrides this block.
<!-- save-claude:end -->
