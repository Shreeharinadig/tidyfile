# Design notes

Write these in your own words as you build. Interviewers ask about decisions, not code, so each section should say what you chose, what you rejected, and why.

## Problem and scope

What problem does this solve, for whom, and what is deliberately out of scope?

## Architecture

Why an API plus a queue plus a worker, instead of one service? Why is the worker the only component that calls the LLM?

## Multi-tenancy

Why row-level security instead of only filtering in application code? What are its limits (superusers bypass it, the login lookup problem)?

## Reliability

How do retries, the dead-letter queue, and idempotency by content hash fit together? What happens if the worker dies mid-job?

## LLM usage

Why does the model return a spec instead of SQL? How are outputs validated, masked, cached, and cost-limited?

## Evaluation

How was the benchmark built, what does it not measure, and how did accuracy change per prompt version?

## Known limits and next steps

What would you change for real production use (managed database, Fargate, Terraform, real auth)?
