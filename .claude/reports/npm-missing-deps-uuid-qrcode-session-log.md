# npm missing dependencies: uuid + qrcode.react — session log

جلسة: npm-missing-dependencies-uuid-qrcode
تاريخ البدء: 2026-08-31
مصدر الاكتشاف: جلسة frontend-mechanical-fix-all-domains-pass1 (نفس اليوم)

## الحالة الحالية (آخر تحديث: بعد سؤال المستخدم عن دعم المتصفح)

التحقيق **مكتمل بالكامل** بما فيه سؤال المستخدم الإضافي عن الحد الأدنى
لدعم المتصفح (راجع الخطوة 3.5 أدناه للإجابة الكاملة بالمراجع). **لا يوجد
تعارض** — `crypto.randomUUID()` آمن للاستخدام (لا browserslist مُقيِّد،
الإنتاج HTTPS إجباري عبر cert-manager، والتطوير المحلي secure context
تلقائيًا). التوصية النهائية (الخطوة 4) جاهزة ومعروضة على المستخدم.

## التنفيذ — بعد موافقة المستخدم

### uuid (21 ملف) — مكتمل ومتحقَّق منه ✅
تم استبدال كل استيراد `import { v4 as uuidv4 } from 'uuid';` بدالة محلية
`generateIdempotencyKey()` (نفس النمط الدفاعي الموجود فعليًا في
`hooks/finance/useTransfer.ts`/`useCheckout.ts` — **قرار: لم يتم استخراج
utility مشتركة في `lib/`**، لأن النمط القائم فعليًا في المشروع هو دالة
محلية داخل كل ملف مش دالة مشتركة؛ عمل ملف `lib/` جديد كان هيبقى نمط
تالت مختلف، تغيير بنيوي زيادة عن النطاق المتفق عليه).

تحقّق:
- `grep -r "from 'uuid'|uuidv4"` بعد التعديل = **0 نتيجة** في كل المشروع.
- `tsc --noEmit`: 1002 خطأ إجمالي (كان 1023 قبل الدفعة) — **فرق 21 بالظبط**،
  صفر خطأ متبقي يذكر uuid.
- اختبار Node مباشر: الدالة المحلية بترجع UUID v4 صحيح (RFC 4122) في كل
  مرة (5 عينات اتفحصت بـregex، كلها `true`)، ومثال المفتاح النهائي
  `bid-42-06fe1f68-17fc-4c7a-896b-88b494791ffd` مطابق تمامًا لشكل
  الاستخدام الأصلي.

### qrcode.react — **محظور مؤقتًا بمشكلة غير متعلقة بالمهمة** ⚠️
`npm install qrcode.react@^4.2.0` **فشل** بخطأ `ERESOLVE`:
```
peer wagmi@"^2.9.0" from @rainbow-me/rainbowkit@2.2.11
Conflicting peer dependency: wagmi@3.6.16 (المثبت فعليًا في المشروع)
```
هذا **تعارض موجود بالفعل في المشروع من قبل** بين `@rainbow-me/rainbowkit@2.2.11`
و`wagmi@3.6.16` — مفيش علاقة له بـqrcode.react نفسها، وظهر بس لأن أي
`npm install` جديد بيفعّل فحص peer dependencies على الشجرة كلها.

**تحقَّق: صفر تغيير حصل.** `git status package.json package-lock.json` =
صفر نتيجة، و`node_modules/qrcode.react` غير موجود — الفشل كان قبل أي
كتابة فعلية.

**محتاج قرار من المستخدم:** إما `--legacy-peer-deps` (يتجاهل فحص peer
deps، ما يغيّرش نسخ فعلية)، أو حل تعارض rainbowkit/wagmi بشكل منفصل أولاً
(خارج نطاق هذه الجلسة تمامًا)، أو تأجيل qrcode.react لحد ما يتحل. لسه
صفر تنفيذ لـqrcode.react.

## الخطوة 1: grep شامل — مكتمل

### uuid — **21 ملف** (مش ~15 كما قُدِّر أوليًا)
تأكيد كامل: كل ملف بيستورد `import { v4 as uuidv4 } from 'uuid';` **فقط**،
وكل استخدام فعلي هو استدعاء واحد `uuidv4()` جوّه template string لبناء
`idempotencyKey`. **صفر استخدام لأي دالة تانية** من مكتبة uuid (لا v1, لا
v5, لا validate, لا parse, لا NIL). القائمة الكاملة:

1. components/health/EmergencySOSButton.tsx
2. components/arbitration-syndicates/VoteModal.tsx
3. components/arbitration-syndicates/JuryVoteModal.tsx
4. components/tenders-auctions/SubmitBidModal.tsx
5. components/tenders-auctions/PlaceBidModal.tsx
6. components/tenders-auctions/EvaluateBidModal.tsx
7. components/social/SendGiftModal.tsx
8. components/social/PostCard.tsx
9. components/social/ContractCard.tsx
10. app/(dashboard)/transport/deliveries/page.tsx
11. app/(dashboard)/transport/bookings/page.tsx
12. components/realestate/TokenizationExchange.tsx
13. components/projects/ContributionModal.tsx
14. components/marketplace/PurchaseModal.tsx
15. components/invitations/AIAssistantChat.tsx
16. components/insurance/SubscribeModal.tsx
17. components/insurance/SubmitClaimModal.tsx
18. components/insurance/ReviewClaimModal.tsx
19. app/(dashboard)/realestate/property/[id]/page.tsx
20. app/(dashboard)/payroll/page.tsx
21. app/(dashboard)/arbitration-syndicates/licenses/page.tsx

نمط الاستخدام موحّد 100% عبر كل ملف، مثال:
```ts
import { v4 as uuidv4 } from 'uuid';
// ...
const idempotencyKey = `bid-${tenderId}-${uuidv4()}`;
// أو
const [idempotencyKey] = useState(() => `ownership-${uuidv4()}`);
```

### qrcode.react — **ملف واحد فقط**
`components/tourism-sports/TicketCard.tsx:4` — `import { QRCodeSVG } from 'qrcode.react';`
مستخدم لعرض QR code لتذكرة NFT واحدة. لا يوجد أي ملف تاني بيستورد
`qrcode.react` في كامل المشروع (تأكَّد بـgrep شامل).

## الخطوة 2: نسخة React ومدى التوافق — مكتمل

`eppne-web/package.json`: `react: 19.2.4`, `react-dom: 19.2.4`, `next: 16.2.9`,
`@types/node: ^20` (يؤكِّد استهداف Node 20+ — بيئة حديثة بالكامل).

استعلام مباشر من npm registry (قراءة فقط، بدون تثبيت):
```
npm view qrcode.react peerDependencies
→ { react: '^16.8.0 || ^17.0.0 || ^18.0.0 || ^19.0.0' }
أحدث نسخة متاحة: 4.2.0
```
**متوافق تمامًا** مع React 19.2.4 الحالية. النسخة 4.x هي الصح (تصدّر
`QRCodeSVG`/`QRCodeCanvas` بنفس الاسم المستخدم فعليًا في `TicketCard.tsx`
— مفيش داعي لتغيير كود الاستدعاء، بس إضافة الحزمة).

## الخطوة 3: بدائل موجودة بالفعل في المشروع — مكتمل

### uuid → `crypto.randomUUID()` (بديل built-in مناسب 100%)
- بيئة الاستهداف (Node 20+ حسب `@types/node`, وكل المتصفحات الحديثة) بتدعم
  `crypto.randomUUID()` كـ Web Crypto API عالمي (global) بدون أي import —
  متاح من Node 19+ ومن كل المتصفحات الحديثة (Chrome 92+, Firefox 95+,
  Safari 15.4+) منذ سنين طويلة قبل هذا المشروع.
- بما إن الاستخدام الوحيد في الـ21 ملف هو توليد UUID v4 عشوائي واحد لكل
  استدعاء (لبناء idempotency key)، فـ`crypto.randomUUID()` بديل مباشر
  ودقيق 100% لنفس الوظيفة — بيرجّع نفس صيغة UUID v4 (RFC 4122) اللي كانت
  بترجعها `uuidv4()`.
- **صفر تبعية جديدة مطلوبة لـuuid** — الحل الأنسب هنا استبدال بدل تثبيت.

**اكتشاف مهم يعزّز القرار:** فيه **سابقة فعلية موجودة بالفعل في المشروع**
لنفس النمط بالظبط (توليد idempotency key بـ`crypto.randomUUID()`)، في
`hooks/finance/useTransfer.ts` (بتعليق عربي صريح: "✅ توليد Idempotency
Key باستخدام crypto.randomUUID()") و`hooks/commerce/useCheckout.ts`،
وكمان في `components/brand-builder/canvas.tsx` و`hooks/use-brand-builder.ts`
و`store/translation-store.ts`. يعني الاستبدال المقترح **مش حل جديد
بيتقدَّم لأول مرة** — هو مواءمة الـ21 ملف مع نمط قائم بالفعل ومُعتمَد في
المشروع، مش اختراع نمط جديد.

النمط الدفاعي المستخدم فعليًا في المشروع (وليس استدعاء مباشر خام):
```ts
// من hooks/finance/useTransfer.ts وhooks/commerce/useCheckout.ts
if (typeof crypto !== 'undefined' && crypto.randomUUID) {
  return crypto.randomUUID();
}
```
هذا النمط الدفاعي سيُتّبع في الـ21 ملف حفاظًا على الاتساق مع الكونفنشن
القائم فعليًا في المشروع، بدل استدعاء `crypto.randomUUID()` خام مباشر.

### qrcode.react → لا يوجد بديل موجود بالفعل يستاهل الاستخدام
- فيه حزمة `qrcode` (نسخة 1.5.3) موجودة فعليًا في `node_modules` لكنها
  **transitive dependency** بس (مش موجودة في `package.json` مباشرة، ومفيش
  أي ملف كود في المشروع بيستوردها إطلاقًا — تأكَّد بـgrep). لو استخدمناها
  هنلاقي نفسنا محتاجين نكتب wrapper component يدوي بالكامل (canvas/SVG
  rendering) بدل استخدام حزمة جاهزة ومُختبرة ومتوافقة مع React الحالي —
  ده مجهود أكبر بلا داعي لملف استخدام واحد بس.
- **قرار:** لا يوجد بديل built-in أو موجود بالفعل يغني عن `qrcode.react` —
  هي فعلاً وظيفة عرض بصري (SVG rendering) مش حاجة ممكن نستبدلها بـWeb API
  built-in زي حالة uuid.

## الخطوة 3.5: تحقّق دعم المتصفح لـ`crypto.randomUUID()` — طلب المستخدم، مكتمل

`crypto.randomUUID()` يحتاج secure context (HTTPS أو localhost) ومتصفحات
حديثة نسبيًا (Chrome 92+, Safari 15.4+, Firefox 95+). تحقّق فعلي:

1. **لا يوجد `browserslist` معلن**: `grep -n "browserslist" package.json`
   = صفر نتيجة، ولا يوجد ملف `.browserslistrc`. لا يوجد سقف متصفحات
   قديمة مُعلن يتعارض.
2. **الإنتاج مضمون HTTPS**: `k8s/base/ingress.yaml:7-19` —
   `cert-manager.io/cluster-issuer: "letsencrypt-prod"` +
   `nginx.ingress.kubernetes.io/force-ssl-redirect: "true"` + قسم `tls:`
   بـ`secretName: eppne-tls`. شهادة حقيقية + إعادة توجيه إجبارية.
3. **التطوير المحلي آمن تلقائيًا**: `next dev` على `http://localhost` —
   كل المتصفحات تعامل `localhost`/`127.0.0.1` كـsecure context بغض النظر
   عن البروتوكول (معيار W3C قياسي)، فمفيش حاجة لإعداد HTTPS محلي.
4. **دليل سياقي**: المشروع فيه `wagmi`/`viem`/`@rainbow-me/rainbowkit`
   (`package.json:20,45,46`) — ستاك محافظ web3 بيفترض أصلاً متصفحات
   حديثة (MetaMask/WalletConnect)، فمفيش سيناريو واقعي لدعم متصفح أقدم
   من Chrome 92.

**النتيجة: صفر تعارض. `crypto.randomUUID()` آمن للاستخدام في الإنتاج
والتطوير المحلي على حد سواء.**

## الخطوة 4: التوصية النهائية

| الحزمة | عدد الملفات | القرار المقترح | السبب |
|---|---|---|---|
| `uuid` | 21 | **استبدال بـ`crypto.randomUUID()`** في كل الـ21 ملف — صفر `npm install` | الاستخدام الوحيد هو توليد UUID v4 عشوائي؛ built-in مدعوم بالكامل في بيئة المشروع (Node 20+/متصفحات حديثة)، بدون أي تبعية إضافية |
| `qrcode.react` | 1 | **`npm install qrcode.react@^4.2.0`** فعليًا | وظيفة عرض SVG حقيقية، بدون بديل built-in، متوافقة تمامًا مع React 19.2.4 حسب peerDependencies الرسمية |

**كل حزمة ليها قرار مختلف عن التانية** — مش حل موحّد للاثنين، بالظبط
زي ما كان مطروح كخيار رابع في طلب المهمة.

### التنفيذ المقترح لو تمت الموافقة (لسه معلَّق):
1. uuid (21 ملف): حذف `import { v4 as uuidv4 } from 'uuid';`، واستبدال
   كل استدعاء `uuidv4()` بدالة صغيرة محلية أو استدعاء مباشر يتبع نفس
   النمط الدفاعي المستخدم فعليًا في `hooks/finance/useTransfer.ts`
   (`typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : ...`)
   بدل استدعاء خام — بدون أي import إضافي، ومتّسق مع كونفنشن قائم بالفعل
   في المشروع.
2. qrcode.react (1 ملف): `npm install qrcode.react` في `eppne-web/` —
   هيضيف السطر لـ`package.json`/`package-lock.json` تلقائيًا، الكود في
   `TicketCard.tsx` مايحتاجش تعديل (نفس اسم `QRCodeSVG` موجود في v4.x).

**صفر تنفيذ حتى الآن — بانتظار موافقتك الصريحة على الجدول أعلاه.**
