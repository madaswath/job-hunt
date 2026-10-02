# Worker operations

The Python worker claims `scan_jobs` with a lease, recovers expired `running` rows, retries with exponential backoff, and delivers `outbox_events` whose type is allowed (Phase 1: `notification` only).

## Metrics

`GET /api/v1/health` on the worker process (port 8001) reports backlog, failures, retry count, and source health.

## Stuck jobs

Rows with `status=running` and `leased_until < now()` are reclaimed on the next loop. After `max_attempts` (default 5) the job is `failed` and an audit event is written.

## Forbidden actions

The worker must never:

- submit an application
- send email, LinkedIn, or recruiter messages
- mark an outbox event delivered before the outcome row exists
