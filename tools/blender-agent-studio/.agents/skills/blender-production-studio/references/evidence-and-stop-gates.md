# Evidence and stop gates

## Evidence levels

- `diagnostic`: inventory, original bounds, warnings or dependency scan.
- `preliminary`: AABB, proxy collision, sparse frames, origins, transforms or viewer reimport.
- `final`: evaluated geometry, semantic pairs, all relevant frames, locked thresholds, target import
  and saved proof views/reports.

Never promote evidence by renaming it.

## Critical failures

Reject or revise for source overwrite, broken identity, unintended collision, absent required
support, impossible articulation, contact drift/foot sliding, corrupt frame, clipping, missing
dependency, hidden budget overrun, failed export/import, or target conversion not verified.

## Stop and ask

Stop when the next action would publish, overwrite a source, weaken a failed threshold, require
unknown rights/credentials, choose a materially different target, or continue after three failed
corrections in one category.

## Final handoff

Report separately:

1. contract/package completeness;
2. geometry and physical/function evidence;
3. visual or motion quality;
4. budget/performance status;
5. export, independent reimport and target import;
6. rights, limitations and human decision.
