---
name: snowflake-handson-guide
description: Use when walking a learner through this repo's Snowflake guides (docs/guides 00-07) or answering where to start
---
# Guide walker
1. Read `.progress/state.json` (missing until a step is verified; that is normal) and `docs/guides/00-orientation.md` for order (order: 01, 02, 03, 05 transform, 04 governance, 06, 07).
2. For the next step show commands, its "Cost of this step", then run `scripts/verify-step N --execute` after (it records the passed step). Scripts preview by default; add `--execute` only when the learner wants the change made.
3. Docs are bilingual: if you edit a guide, update `docs/ja/guides/` in the same change. Never translate code.
4. Never commit secrets; run `scripts/check-secrets` before any commit.
