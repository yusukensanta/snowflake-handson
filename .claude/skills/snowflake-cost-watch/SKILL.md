---
name: snowflake-cost-watch
description: Use when the user asks about credits, spend, budget, or before starting an expensive step (Dynamic Table lag, Cortex, large loads)
---
# Cost watch
Run `scripts/cost-report` first. Budget: plan 53, warn 70, hard stop 80 credits (assumed $4.50/credit, Seoul rate unverified). Quote the guide step cost before running it. Suggest `scripts/cost-guard --suspend-all --execute` when idle. Resource monitors cover warehouses only: check serverless lines (e.g. `DATA_QUALITY_MONITORING`) in the report. Never raise the resource-monitor quota without asking.
