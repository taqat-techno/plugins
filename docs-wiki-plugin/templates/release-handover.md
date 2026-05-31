# Release Handover: <RELEASE>

> Handover record for a single release. Fill every `<PLACEHOLDER>`; delete guidance lines (`>`) before publishing. One page per release.

| Field | Value |
|-------|-------|
| Release | `<RELEASE_NAME_OR_VERSION>` |
| Release type | `<MAJOR / MINOR / PATCH / HOTFIX>` |
| Target environment | `<ENVIRONMENT>` |
| Planned date/time | `<YYYY-MM-DD HH:MM TZ>` |
| Release manager | `<NAME / ROLE>` |
| Status | `<PLANNED / IN PROGRESS / RELEASED / ROLLED BACK>` |
| Tracking reference | `<TICKET / TAG / PIPELINE LINK>` |

## Summary

State what this release delivers and why, in two or three sentences. Write for a reader who was not involved in the work.

- What changed at a high level: `<PLAIN_LANGUAGE_SUMMARY>`
- Primary driver: `<FEATURE / FIX / COMPLIANCE / PERFORMANCE / OTHER>`
- User-visible impact: `<WHAT_USERS_WILL_NOTICE_OR_NONE>`

## Scope and Changes

List the concrete changes included in this release. Group by category and link each item to its source of record.

| Type | Change | Reference | Owner |
|------|--------|-----------|-------|
| Feature | `<DESCRIPTION>` | `<TICKET_OR_PR>` | `<OWNER>` |
| Fix | `<DESCRIPTION>` | `<TICKET_OR_PR>` | `<OWNER>` |
| Config | `<DESCRIPTION>` | `<TICKET_OR_PR>` | `<OWNER>` |

### Out of scope

Name anything that might be assumed part of this release but is deliberately excluded.

- `<EXCLUDED_ITEM_AND_REASON>`

### Dependencies

Record prerequisites that must be in place before or alongside this release.

- Upstream/services: `<DEPENDENCY_AND_REQUIRED_STATE>`
- Other releases: `<RELATED_RELEASE_OR_NONE>`

## Migration and Upgrade Steps

Ordered steps to apply this release. Each step should be runnable by someone other than the author. Mark any step that requires elevated access or downtime.

1. Pre-flight: confirm prerequisites and take a backup of `<DATA_STORE_OR_STATE>`.
2. Announce/begin maintenance window if required: `<WINDOW_OR_NONE>`.
3. Deploy artifact: `<ARTIFACT_OR_VERSION>` to `<ENVIRONMENT>`.
4. Apply migrations: `<MIGRATION_COMMAND_OR_NONE>`.
5. Update configuration/secrets: `<CONFIG_KEYS_TO_SET (names only, never values)>`.
6. Restart/reload services: `<SERVICE_LIST>`.
7. Run post-deploy tasks: `<CACHE_WARMUP / REINDEX / FEATURE_FLAG_TOGGLE / NONE>`.

> Example (illustrative — not required):
> ```
> # back up state, then apply the release
> backup-tool snapshot --target <store>
> deploy-tool apply --version <RELEASE>
> migrate-tool up
> service-tool restart <service>
> ```

## Verification Checklist

Confirm the release is healthy before declaring it done. Check each item and note evidence (link, screenshot reference, or command output location).

- [ ] Build/artifact matches the intended `<RELEASE>` identifier
- [ ] Migrations completed without error
- [ ] Health check / readiness endpoint returns healthy
- [ ] Smoke test of critical path passes: `<CRITICAL_FLOW>`
- [ ] Automated tests / pipeline green: `<PIPELINE_REFERENCE>`
- [ ] Logs show no new errors after deploy
- [ ] Monitoring/alerts show normal metrics: `<METRIC_OR_DASHBOARD_REFERENCE>`
- [ ] Configuration/feature flags set as intended
- [ ] Stakeholder/owner confirmed expected behavior

## Known Issues

List defects, limitations, or risks shipping with this release so the on-call and support teams are not surprised.

| Issue | Impact | Workaround | Tracking |
|-------|--------|------------|----------|
| `<DESCRIPTION>` | `<WHO_IS_AFFECTED_AND_HOW>` | `<WORKAROUND_OR_NONE>` | `<TICKET_REFERENCE>` |

If there are none, state: `No known issues at release time.`

## Rollback

Define how to revert if verification fails or the release causes a regression. The rollback path must be tested or at least reviewed before release.

- Decision trigger: `<CONDITION_THAT_WARRANTS_ROLLBACK>`
- Decision owner: `<NAME / ROLE>`
- Data considerations: `<IS_ROLLBACK_DATA_SAFE / MIGRATION_REVERSIBILITY>`

Rollback steps:

1. Stop further traffic/deploys if needed: `<ACTION_OR_NONE>`.
2. Revert artifact to previous good version: `<PREVIOUS_VERSION>`.
3. Revert/restore migrations or data: `<DOWN_MIGRATION_OR_RESTORE_PROCEDURE>`.
4. Restart affected services: `<SERVICE_LIST>`.
5. Re-run the verification checklist against the reverted state.
6. Communicate rollback to stakeholders: `<CHANNEL_OR_RECIPIENTS>`.

## Sign-off

Each party confirms their area is ready before the release is considered complete.

| Role | Name | Decision | Date |
|------|------|----------|------|
| Release manager | `<NAME>` | `<APPROVED / HOLD>` | `<YYYY-MM-DD>` |
| Engineering owner | `<NAME>` | `<APPROVED / HOLD>` | `<YYYY-MM-DD>` |
| QA / Verification | `<NAME>` | `<APPROVED / HOLD>` | `<YYYY-MM-DD>` |
| Product / Business owner | `<NAME>` | `<APPROVED / HOLD>` | `<YYYY-MM-DD>` |

### Post-release notes

Capture anything learned during execution that should inform the next release.

- What went well: `<NOTE>`
- What to improve: `<NOTE>`
- Follow-up actions: `<ACTION_AND_OWNER>`
