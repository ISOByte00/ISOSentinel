\# ISOSentinel — Project Instructions



\## Project Goal

ISOSentinel is a Python-based YKS study discipline and session management application. The immediate goal is to finish version 0.1, not to design the entire future product.



\## Highest Priority Rule

\*\*Evaluate every change against the actual v0.1 requirements and current repository state.\*\*



Do not prematurely refactor functioning components, introduce abstractions without a concrete need, or expand the scope toward future features while essential v0.1 functionality remains incomplete.



\## Before Every Task

1\. Inspect the relevant source files and current Git state.

2\. Read the existing implementation before suggesting a rewrite.

3\. Identify what is already implemented, what is incomplete, and what is actually broken.

4\. Check relevant callers, event handlers, persistence logic, and tests before modifying interfaces.

5\. Ask for clarification only when a missing decision genuinely blocks safe progress.



Never assume that an item mentioned in an old conversation or README is implemented. Verify it in the current source.



\## Architecture and Existing Context

The project is being developed in Python with a modular architecture. Existing and planned areas include:

\- `main.py`: application entry point.

\- `ui/`: dashboard and user interface.

\- `core/`: session management, process monitoring, and application logic.

\- `database/`: persistent storage.

\- `ai/`: local AI and optional cloud AI integrations.

\- `config.json`: application configuration.



These are contextual expectations, not permission to create missing modules blindly. Follow the actual repository structure.



Previous development context included:

\- Event Bus connections.

\- Session state transitions, including `IDLE` to `STUDYING`.

\- Session creation and session IDs.

\- Process Guard activation and process detection.

\- Logging of detected violations.

\- Recovery/cancellation behavior that needs verification.



These items may have changed. Inspect the current code and Git history before treating them as completed or broken.



\## Scope Control

\- Finish essential v0.1 behavior before working on browser extensions, mobile integrations, advanced cloud analytics, or other future features.

\- Do not propose unrelated Event Bus unsubscribe refactors, enum refactors, or architectural cleanups unless they block a concrete requirement or fix a demonstrated bug.

\- Do not rewrite large sections of code to fix a small issue.

\- Do not add dependencies without explaining why they are necessary.

\- Do not silently change database schemas, configuration formats, event contracts, or session lifecycle behavior.



\## Implementation Rules

\- Make the smallest complete change that solves the requested problem.

\- Preserve existing behavior unless the requirement explicitly changes it.

\- Consider error handling, application shutdown, session cancellation, persistence, and process-monitoring edge cases when relevant.

\- Avoid fake implementations, placeholder success states, and features that appear functional but do not perform their intended work.

\- Update tests and documentation when the change requires it.

\- Run relevant tests or checks where possible and report the actual results.

\- Do not claim a feature works merely because its code exists.



\## Milestone Review

When asked to evaluate the project, a commit, or a push:

1\. Inspect the actual current branch and working tree.

2\. Review the relevant diff and affected files.

3\. Determine whether the change advances v0.1.

4\. Identify regressions, missing behavior, and untested critical paths.

5\. Separate blocking issues from optional improvements.

6\. Recommend the single most valuable next step.



Do not turn every review into a general architecture redesign.



\## Expected Response Style

Use Turkish by default. Be direct, technical, and concise.

When proposing code changes, explain the cause and expected behavior, then provide complete updated files when practical.

When debugging interactively, give one actionable step at a time and wait for the result.

Clearly distinguish verified facts from assumptions.



