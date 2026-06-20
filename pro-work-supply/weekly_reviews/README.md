# PWS weekly ops reviews

Dated reports written by the `pws-weekly-ops` scheduled task (runs every Friday ~9:23am local). One file per run, named `YYYY-MM-DD.md`.

Each report covers the trailing 7 days for the Stage 1 Shopping campaign (`23958300224`) and contains the pulled metrics plus a "Proposed actions" section: bid (max CPC) change, roster prunes (DFW `PWS_Stage1` lookup), negative keywords, and the tripwire / Stage-2-unlock verdict. Every item is a PROPOSAL pending Adam's approval -- the task itself makes no account or feed changes.

This folder lives in the Dropbox-synced project, so reports are readable from any machine. The scheduled task definition lives per-machine at `~/.claude/scheduled-tasks/pws-weekly-ops/SKILL.md`; recreate it on a second machine if you want it to fire there too.
