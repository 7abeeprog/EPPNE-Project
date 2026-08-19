# `test_invitations_savepoint_leak.py`

## المرجع الأصلي
- `.claude/reports/invitations-savepoint-leak-session-log.md` (Backlog #11a، جلسة `invitations-user-registration-savepoint-leak`).
- الدليل الحي الأصلي للباج: `users id=52` (`p_ctor_inv_newuser@eppne.com`, tenant_id=1) — **لم يُلمَس ولن يُلمَس** في هذا الملف ولا في أي test مستقبلي (نفس الالتزام الموثَّق في التقرير، قسم 3.0/7.0).

## السبب الجذري (كان) — ملخص
`InvitationsService.accept_invitation` كانت بتنادي `_create_user_from_invitation`
*جوه* `self.db.begin_nested()`، و`UserRepository.create()`/`WalletRepository.create()`
(`identity/repository.py`) بتعمل `commit()` مباشر — ده كان بيقفل السطر
الـSAVEPOINT فيسيب يوزر حقيقي على القرص **بلا محفظة** لو أي كود بعده كراش،
والدعوة تفضل `SENT` بلا أي مسار نجاح ممكن حتى لو اتعادت المحاولة.

## الإصلاح المُطبَّق (`app/domains/invitations/service.py` فقط)
1. نقل استدعاء `_create_user_from_invitation` بره `begin_nested()` بالكامل.
2. تثبيت `idempotency_key` الممرَّر لـ`UserService.register()` بصيغة
   `f"INV-ACCEPT-T{tenant_id}-{invitation_id}"` بدل `uuid.uuid4()` عشوائي —
   لضمان أن إعادة المحاولة بعد فشل جزئي تستخدم نفس اليوزر (`get_by_idempotency_key`)
   بدل ما تفشل بـ`ValidationError("البريد الإلكتروني مسجل بالفعل")` أو تنشئ يوزر مكرَّر.

## إيه اللي بيتحقق منه هذا الملف (مطابق لما اتحقق حيًا في التقرير الأصلي، قسم 7)

### `test_accept_invitation_clean_creates_user_with_wallet`
سيناريو "قبول نظيف" (يعادل دعوة `id=2` / `P-SAVEPOINT-FIX-VERIFY-CLEAN` في التقرير):
- `accept_invitation` بيتنادى مرة واحدة بدون فشل.
- بعد النجاح: يوزر واحد موجود على القرص **بمحفظة كاملة** (`wallets` عليها صف)،
  الدعوة `status == ACCEPTED`، `current_uses == 1`.

### `test_accept_invitation_retry_after_partial_failure_is_idempotent`
سيناريو "فشل جزئي متعمَّد بعد إنشاء اليوزر ثم إعادة محاولة" (يعادل دعوة `id=3` /
`P-SAVEPOINT-FIX-VERIFY-RETRY` في التقرير):
- `InvitationsRepository.create_lead` بيتعطَّل مؤقتًا (monkeypatch) ليفشل **مرة
  واحدة بس** بـ`RuntimeError` — بيحاكي كراش حقيقي جوه `begin_nested()` بعد ما
  اليوزر اتعمل خارجها.
- **بعد المحاولة الأولى الفاشلة:** يتأكد إن اليوزر **لسه موجود بمحفظة كاملة**
  رغم الفشل (ده تحديدًا إثبات إصلاح "يوزر بلا محفظة")، والدعوة لسه `SENT`.
- **بعد المحاولة الثانية (retry ناجح):** يتأكد إن **نفس اليوزر** اتستخدم (صفر
  تكرار — `len(users) == 1`)، والدعوة بقت `ACCEPTED`، و`current_uses == 1`
  مش `2` (يعني الـretry ما ضاعفش العداد).

## استثناءات / حدود موثَّقة
- **لا يوجد `xfail`/`skip` في هذا الملف** — كل السيناريوهات المذكورة في التقرير
  اتحققت بالكامل (Full)، مفيش جزء مؤجَّل.
- `InvitationsService._check_saas_limits` بيتعطَّل (`monkeypatch`, no-op) في
  الـtestين — نفس أسلوب سكريبت التحقق الحي الأصلي (`verify_savepoint_fix.py`،
  التقرير قسم 7.2)، لأن tenant_id=1 عنده اشتراك SaaS فعلي لكن بدون feature
  `"crm"` — ده منطق مستقل تمامًا (Backlog #9)، مش جزء من نطاق هذه الجلسة.
- فجوة `expires_at`/`max_uses` غير المفعَّلة في `accept_invitation` **خارج
  نطاق هذا الملف عمدًا** — موثَّقة في التقرير الأصلي كبند Backlog منفصل
  (`invitations-missing-expiry-max_uses-validation`)، صفر تحقق أو إصلاح لها هنا.

## بيانات throwaway
- `tenant_id=1` ("Local Test Tenant") — نفس المستأجر throwaway المستخدم في
  التحقق الحي الأصلي.
- كل test بيعمل دعوة (`sovereign_invitations_v2`) ويوزر بإيميل فريد
  (`p_regtest_savepoint_{clean,retry}_<uuid8>@eppne.com`) عبر `uuid4` — صفر
  تصادم بين تشغيلات متتالية.
- تنظيف كامل في `finally` بعد كل test (يوزر + محفظة + lead + interaction +
  الدعوة نفسها) — تأكَّد بـ`SELECT` مباشر بعد التشغيل: صفر صفوف متبقية.

## ملاحظة بنية تحتية (test infra، مش كود إنتاج)
على ويندوز، `pytest-asyncio` بيفتح event loop جديد لكل test function، لكن
`engine`/`redis_client` العالميين (`app/core/database.py`, `app/core/redis_client.py`)
بيحتفظوا باتصالات من loop سابق فتنكسر (`RuntimeError: Event loop is closed`).
الحل (`await engine.dispose()` + `await redis_client.close()`) موجود في fixture
`db` المشتركة بـ`tests/conftest.py` — مش في هذا الملف، ومتاح لكل ملفات
regression-tests-backfill بلا تكرار كود.

## طريقة التشغيل
```
./venv/Scripts/python.exe -m pytest tests/test_invitations_savepoint_leak.py -v
```
يحتاج DB حقيقي شغّال (`docker` container `eppne_db`, بورت 5435) وRedis شغّال
(بورت 6380) — الملف بيستخدم اتصالات حقيقية، صفر mock/stub لقاعدة البيانات.

**آخر تشغيل مُوثَّق:** 2 passed (راجع `PROGRESS_LOG.md` لتفاصيل الجلسة الكاملة).
