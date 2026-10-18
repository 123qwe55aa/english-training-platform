# Codex management tools

The Codex skill uses a discoverable JSON tool registry through Django's management command. It can list/read students, courses and materials; create or update records; stage uploads; prepare sessions; record teacher-confirmed progress; award points; and inspect its audit history. The website itself has no chat assistant and exposes no anonymous write API.

## Setup

The CLI lives at `scripts/teaching_agent.py`. Local development calls require `--local`. Remote use requires SSH access and the private environment variables `ENGLISH_PLATFORM_SSH_HOST` and `ENGLISH_PLATFORM_REMOTE_DIR`. The remote directory must contain the Compose project and the app service must be named `app`. Do not place SSH private keys or host-specific values in the repository.

```sh
python3 scripts/teaching_agent.py --local tools
python3 scripts/teaching_agent.py --local call students.list
```

Mutations default to preview. Review the returned changes before applying. Stable request IDs make retries idempotent; revisions prevent stale edits from overwriting newer data. A transport timeout must be reconciled through the operation history before issuing a new award.

## Data safeguards

- Never infer progress, speaking ability or consent from page views.
- New records default to unpublished. Explicitly check publication and assignment before sharing a learner-facing link.
- Keep teacher notes and evidence private. Require clear authorization before publishing learner information or recordings.
- Uploads are staged privately and referenced by opaque handles, not server paths.
- Materials supplied by third parties remain subject to their owners' terms. The tool does not automatically download source links or generate lesson content with an LLM.
