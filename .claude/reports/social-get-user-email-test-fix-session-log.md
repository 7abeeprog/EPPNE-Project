# Session Log — `backlog-social-get-user-email-tenant-mismatch-behavior` — Test Fix

**Date:** 2026-09-08
**Scope:** Test-only change. **Zero edits to `social/service.py` or any production code.**

## Background

Backlog item opened 2026-09-07 (`PROGRESS_LOG.md`) flagged that
`test_social_get_user_email_correct_and_wrong_tenant`
(`eppne-backend/tests/test_user_repository_get_by_id_audit.py`) expected
`_get_user_email` (`social/service.py:718-724`) to return a text fallback
(`f"user_{user.id}@eppne.com"`) for a mismatched tenant, while the actual
code raises `NotFoundError` explicitly. This left an open design question:
is the explicit exception correct (test is stale), or is a fallback
actually required (code is incomplete)?

## Verification

Read `social/service.py:718-724`:

```python
async def _get_user_email(self, user_id: int, tenant_id: int) -> str:
    from app.domains.identity.repository import UserRepository
    user_repo = UserRepository(self.db)
    user = await user_repo.get_by_id(user_id, tenant_id)
    if not user:
        raise NotFoundError("Receiver not found in your tenant")
    return cast(str, user.email)
```

No fallback path exists anywhere in this function — a wrong tenant always
raises `NotFoundError`. This is also consistent with the sibling call site
at `social/service.py:578`, which already carries a comment confirming the
intent: `# raises NotFoundError if receiver is outside your tenant`.

**Conclusion:** the explicit exception is the correct, intended behavior.
The old test's expectation of a string fallback does not match any code
path that currently exists (and per the investigation this backlog item
branched from, it never touched — `social/service.py` was untouched by
the referral/affiliate unification in `2960d9d`). The test was simply
written against stale/incorrect expectations.

## Change made

`eppne-backend/tests/test_user_repository_get_by_id_audit.py`,
`test_social_get_user_email_correct_and_wrong_tenant`:

- Replaced the fallback-string assertion with `pytest.raises(NotFoundError)`
  around the wrong-tenant call, matching the pattern already used
  elsewhere in the same file (e.g. line 172) and using the `NotFoundError`
  import already present at line 76 — no new imports needed.
- Updated the docstring to describe the actual (exception) behavior
  instead of the old fallback description.

No other lines, and no non-test files, were touched.

## Test run

```
tests/test_user_repository_get_by_id_audit.py::test_social_get_user_email_correct_and_wrong_tenant PASSED [100%]
1 passed, 14 deselected, 2 warnings in 46.79s
```

## PROGRESS_LOG.md

**Correction:** an earlier pass in this session appended a new dated
entry (`## [2026-09-08] ...`) instead of editing the original backlog
entry in place, based on a misreading of the file's append-only
convention. That convention applies only to the "الجلسات المُقفلة"
closed-sessions log — per `PROGRESS_LOG.md` line 5, the backlog itself
("جدول الـBacklog") is updated by editing the existing entry in place,
not by appending. The appended entry was removed, and the original
`## [2026-09-07] backlog-social-get-user-email-tenant-mismatch-behavior`
entry was updated in place instead: its heading now reads `✅ اتحل
[تحديث 2026-09-08] — الكود سليم كما هو، تم تحديث الاختبار ليتوقّع
NotFoundError صريح بدل fallback نصي قديم`, and a `[تحديث 2026-09-08]`
paragraph was added to the entry body recording the resolution and
linking to this report.
