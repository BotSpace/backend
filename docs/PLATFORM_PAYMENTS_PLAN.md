# Platforma to'lovlari — texnik reja (Botspace bot to'lovlari)

> Maqsad: bot egasi to'lov tizimi bilan **o'zi integratsiya qilmasdan**, bot
> foydalanuvchilaridan (mijozlardan) **Botspace orqali** pul qabul qiladi.
> Pul Botspace'ning Click hisobiga tushadi, egasining balansiga (komissiya
> ushlanib) yoziladi, ega pulni **admin orqali qo'lda** kartasiga/naqd yechadi.

Holat: REJA (kod yozilmagan). Tasdiqlangan qarorlar 1-bo'limda.

---

## 1. Tasdiqlangan qarorlar

| Mavzu | Qaror |
|---|---|
| Merchant | **Botspace** yagona Click merchant (shartnoma Botspace'da). Egalar Click bilan ishlamaydi. |
| Payout | **Qo'lda** — ega "pul yechish" so'rovi, admin kartaga/naqd o'tkazadi, "bajarildi" deydi. Click payout API kerak emas. |
| Checkout UX | **To'g'ridan Click havola** (tugma → Click sahifasi brauzerda). Web App keyin. |
| Provayder | **Click** (kod provider-agnostic; Payme/Uzum keyin). |
| Komissiya | **Sobit %** (default 5%, admin sozlaydi). |
| Kreditlash | Mijoz to'lovi egaga **darhol** yoziladi; **yechish** so'rovini admin ko'rib chiqadi (tabiiy hold). |
| Min. yechish | 50 000 so'm (sozlanadi). |
| Valyuta | UZS (so'm). |

### Hal qilinmagan / kelajak
- Refund/chargeback: agar to'lov qaytarilsa va ega allaqachon yechib bo'lgan bo'lsa — kim qoplaydi? MVP: refund'ni admin qo'lda boshqaradi, balans manfiyga tushishi mumkin (keyin rezerv/T+N hold qo'shiladi).
- Soliq/KYC: Botspace pulni ushlab turishi — yuridik masala (biznes hal qiladi). Kodga ta'sir qilmaydi.
- Web App checkout, Payme/Uzum, avtomatik Click payout.

---

## 2. Mavjud infratuzilma (qayta ishlatiladi)

| Komponent | Fayl | Qanday ishlatiladi |
|---|---|---|
| Click merchant + webhook (imzo tekshiruvi) | `payment/views/click.py`, `payment_link` | Pay-link generatsiya + to'lov tasdiq webhook |
| Balans + idempotent ledger | `payment/services/balance.py` (`balance_service.add/subtract`, `HistoryModel`) | Egaga net kreditlash, komissiya yozish |
| `User.balance` (BigInt, so'm) | `accounts/models/user.py` | Bot egasining daromad balansi |
| Withdrawal (admin tasdiq) | `template/models/withdrawal.py`, `template/enums/withdrawal.py` | Pul yechish oqimi namunasi — umumlashtiriladi |
| Order + komissiya namunasi | `template/models/order.py` (`commission_paid`) | PaymentOrder dizayni uchun namuna |
| Engine tashqi webhook | `engine-golang: controller/webhook.go` — `POST /custom-webhook/{provider}/{chat_id}` → `ExternalWebhookTriggerNode` | To'lov tasdiqlanganda flow'ni davom ettirish |
| Engine↔backend kanal | `X-Internal-Token` / `INTERNAL_API_TOKEN`, `API_URL`/`API_TOKEN` | Engine backend'da order yaratadi; backend bot containeriga signal yuboradi |

**Asosiy xulosa:** ~70% bor. Yangi narsa: PaymentOrder modeli, webhook'ni **egaga** yo'naltirish, engine to'lov node'i, daromad dashboardi, withdrawalни umumlashtirish.

---

## 3. Pul oqimi (end-to-end)

```
1. Bot flow'da "Botspace To'lov" node ishga tushadi (amount=10000, comment="Buyurtma #42")
2. Engine → backend: POST /api/payment/order/create/ (X-Internal-Token)
      body: {project_id, payer_chat_id, amount, comment, provider:"click"}
   ← backend: {order_id, pay_url}   (PaymentOrder.status=created)
3. Engine mijozga inline-tugma yuboradi: [ To'lash → pay_url ]  va flow PAUZA
4. Mijoz Click'da to'laydi → pul Botspace Click hisobiga
5. Click → backend webhook (payment/click) → imzo tekshiriladi
      - order topiladi (merchant_trans_id == order_id)
      - komissiya = amount * rate;  net = amount - komissiya
      - balance_service.add(owner, net, idem="payorder:credit:{order_id}")
      - balance_service.add(BOTSPACE_REVENUE_USER, komissiya, ...)  // yoki alohida hisob
      - order.status=paid, paid_at, commission, net
6. Backend → bot engine: POST {bot_engine}/custom-webhook/click/{payer_chat_id}
      body: {order_id, amount, net, status:"paid", comment}
7. Engine: ExternalWebhookTriggerNode(provider="click") ishga tushadi
      context: payment_order_id, payment_amount, payment_net, payment_status
   → flow success branch davom etadi ("Rahmat, to'lov qabul qilindi ✅")

Keyin (egasi pul yechadi):
8. Dashboard → POST /api/payment/withdrawal/  {amount, card_number, card_owner}
      - balance yetarli + amount>=min tekshiriladi
      - WithdrawalRequest.status=pending
9. Admin panel → tasdiq → admin qo'lda kartaga o'tkazadi → "approved"
      - balance_service.subtract(owner, amount, idem="withdrawal:{id}")
   yoki rad → "rejected" (balans tegmaydi)
```

---

## 4. Backend dizayni

### 4.1 Yangi model: `PaymentOrderModel` (`payment/models/order.py`)
```
project        FK ProjectModel        # qaysi bot
owner          FK User                # bot egasi (project.user) — kreditlanadi
payer_chat_id  BigInteger             # to'lovchi Telegram chat_id
amount         Decimal(20,2)          # to'liq summa (so'm)
commission     Decimal(20,2) = 0      # Botspace ulushi
net_amount     Decimal(20,2) = 0      # egaga = amount - commission
provider       Char (PaymentMethosEnum, default click)
status         Char (created/paid/cancelled/refunded)
external_id    Char null              # Click trans id
comment        Char null              # mijozga ko'rinadigan izoh
idempotency_key Char unique null
created_at / paid_at
```
- `merchant_trans_id` = `order_id` (Click webhook shu bo'yicha topadi).
- Komissiya foizi: `OptionsModel(key="payment_commission_percent")` yoki settings — admin sozlaydi.

### 4.2 API endpointlar
| Endpoint | Auth | Vazifa |
|---|---|---|
| `POST /api/payment/order/create/` | **X-Internal-Token** (engine) | Order yaratadi, Click pay_url qaytaradi |
| `GET /api/payment/order/{id}/status/` | Internal yoki egasi | Order holati (engine reconnect'da tekshiradi) |
| `GET /api/payment/earnings/` | Egasi (JWT) | Balans + mijoz to'lovlari ro'yxati (PaymentOrder, status=paid) |
| `POST /api/payment/withdrawal/` | Egasi (JWT) | Pul yechish so'rovi |
| `GET /api/payment/withdrawal/` | Egasi | O'z so'rovlari ro'yxati |
| `POST /api/admin/.../withdrawal/{id}/approve\|reject/` | Admin | Tasdiq/rad (balansni o'zgartiradi) |

### 4.3 Click webhook kengaytirish
Hozir `ClickWebhookAPIView` `TransactionModel` (egasi balans to'ldirish) bilan ishlaydi.
**Muammo:** bitta webhook ikki xil obyektga (TransactionModel vs PaymentOrderModel) ishlashi kerak.
**Yechim:** `merchant_trans_id` prefiks bilan ajratiladi (masalan `ord_<id>` vs `txn_<id>`), yoki ikkita alohida Click `service_id`/endpoint. Tavsiya: **alohida webhook URL** (`/api/payment/click/order-update/`) + alohida `merchant_trans_id` namespace — eski oqimga tegmaslik uchun.

### 4.4 Withdrawal — umumlashtirish
- `template/models/withdrawal.py` (`TemplateWithdrawalRequestModel`) — namuna.
- Variant A: yangi `PaymentWithdrawalRequestModel` (bot daromadi uchun, `User.balance`dan).
- Variant B: mavjudni umumiy `WithdrawalRequestModel`ga ko'chirish (source: template/bot).
- Tavsiya MVP: **alohida `PaymentWithdrawalRequestModel`** (template'ga tegmaslik), keyin birlashtirish.

---

## 5. Engine dizayni (Go)

### 5.1 Yangi node: `BotspacePaymentNode` (yoki `PlatformPaymentNode`)
data: `amount` (yoki `{{var}}`), `comment`, `provider` (default click), `buttonText` (default "To'lash").
- `Handle()`: backend `/api/payment/order/create/` chaqiradi (API_URL+API_TOKEN/X-Internal-Token), `pay_url` oladi, mijozga inline URL tugma yuboradi, flow pauza qiladi (`wait`).
- Handle'lar: `source-default` (link yuborildi), va to'lov natijasi **alohida** — pastга qarang.

### 5.2 To'lov natijasini kutish — 2 variant
- **A (mavjud mexanizmni qayta ishlat):** node faqat order yaratib link yuboradi; foydalanuvchi alohida `ExternalWebhookTriggerNode(provider="click")` qo'yadi (global) → backend `/custom-webhook/click/{chat_id}` ga POST qiladi → trigger ishlaydi. **Eng kam ish, hozir ishlaydi.**
- **B (qulayroq UX):** `BotspacePaymentNode`ning o'zida `paid`/`failed` branch handle'lari; backend signali kelganda paused flow'ni o'sha node'dan davom ettirish. Ko'proq engine ishi (state'ga order_id bog'lash, resume).
- **Tavsiya:** MVP'da **A**, keyin **B** bilan UX yaxshilanadi.

### 5.3 Context o'zgaruvchilari (webhook payload'dan)
`payment_order_id`, `payment_amount`, `payment_net`, `payment_status`, `payment_comment`.

---

## 6. Frontend

### 6.1 Dashboard (bot egasi)
- **"Daromad" sahifasi:** umumiy balans, mijoz to'lovlari ro'yxati (filter: bot/sana/status, pagination), komissiya breakdown.
- **"Pul yechish":** balans, "Yechish" tugmasi → karta raqami/egasi/summa modal → so'rov; so'rovlar tarixi (pending/approved/rejected).
- (Qoidaga ko'ra: list sahifa = filter + pagination + detail.)

### 6.2 Panel (constructor)
- `BotspacePaymentNode` UI: amount, comment, buttonText, provider (hozir Click). Variant B bo'lsa paid/failed branch.

### 6.3 Admin panel
- Withdrawal navbati: pending so'rovlar, tasdiq/rad (rad sababi), kim ko'rdi.
- Komissiya % sozlamasi.
- (Ixtiyoriy) PaymentOrder reconciliation jadvali.

---

## 7. Xavfsizlik / to'g'rilik

| Tahdid | Himoya |
|---|---|
| Soxta webhook | Click imzo tekshiruvi (mavjud `ClickWebhook.check_auth`) |
| Summani buzish | Summa **order'dan** olinadi (DB), webhook/flow'dan emas |
| Ikki marta kreditlash (webhook retry) | `idempotency_key="payorder:credit:{order_id}"` (balance_service idempotent) |
| Double-spend yechishda | Withdrawal `@transaction.atomic` + `select_for_update`, balans tekshiruvi |
| Flow container restart | Order = haqiqat manbai; engine reconnect'da `/order/{id}/status/` so'raydi |
| Refund (chargeback) | MVP: admin qo'lda; keyin T+N hold/rezerv |
| Manfiy balans | `subtract`da balans tekshiruvi; admin payout faqat yetarli balansda |

---

## 8. Bosqichli reja

### Faza 1 — Backend MVP (prodga chiqarmasdan test)
1. `PaymentOrderModel` + migratsiya
2. `POST /order/create/` (X-Internal-Token) — order + Click pay_url
3. Alohida Click order-webhook — egaga net kreditlash + komissiya + order.paid; backend→bot `/custom-webhook/click/{chat_id}` POST
4. `GET /order/{id}/status/`, `GET /earnings/`
5. Komissiya % konfiguratsiya (OptionsModel)
6. Testlar: order yaratish, webhook idempotency, komissiya hisobi, balans
- **Acceptance:** prod debug bot orqali — order yaratiladi, qo'lda webhook simulyatsiya → egasi balansi net qadar oshadi, ikki marta webhook → bir marta kredit.

### Faza 2 — Engine
1. `BotspacePaymentNode` (order yaratish + link tugma + pauza)
2. Variant A resume (ExternalWebhookTrigger) hujjatlash; context o'zgaruvchilari
3. Engine testlari; engine tag + prod version bump
- **Acceptance:** botda /start → to'lov node → Click link → (test to'lov) → success branch.

### Faza 3 — Panel + Dashboard
1. Panel: node UI (manifest) + agentv3 catalog/data-model + docs
2. Dashboard: Daromad sahifasi + Pul yechish
- **Acceptance:** egasi botga payment node qo'shadi; mijoz to'lovini va balansni dashboardда ko'radi.

### Faza 4 — Payout + Admin
1. `PaymentWithdrawalRequestModel` + egasi API
2. Admin: tasdiq/rad oqimi (balans subtract), komissiya sozlamasi
- **Acceptance:** ega yechish so'raydi → admin tasdiqlaydi → balans kamayadi; rad → tegmaydi.

### Faza 5 — Polish (kelajak)
Web App checkout, Payme/Uzum, avtomatik Click payout, refund/hold rezervi, reconciliation hisobotlari.

---

## 9. Repolar bo'yicha ish hajmi (taxminiy)

| Repo | Faza | Hajm |
|---|---|---|
| backend | 1, 4 | O'rta (model, webhook, withdrawal, testlar) |
| engine-golang | 2 | O'rta (1 node + resume) |
| bot-constructor-panel | 3 | Kichik (manifest node UI) |
| agentv3 | 3 | Kichik (catalog + data-model + docs) |
| dashboard | 3 | O'rta (2 sahifa) |
| admin | 4 | Kichik-o'rta (withdrawal navbati) |

---

## 10. Yakuniy qarorlar (tasdiqlandi)
1. **Komissiya egadan ushlanadi:** mijoz `amount` to'laydi (10000), ega `net = amount - amount*rate` oladi (9500), Botspace `commission` (500).
2. **Bitta umumiy balans** (`User.balance`), ammo hisobotda **pul qaysi botdan tushgani** ko'rsatiladi (`PaymentOrder.project` orqali — bot bo'yicha guruhlash).
3. To'lov summasi: min 1000 so'm, max yo'q (keyin sozlanadi).
4. **Bitta Click `service_id`** — eski (obuna balans to'ldirish, `TransactionModel`) va yangi (bot to'lovi, `PaymentOrder`) bitta webhook'ga keladi, `merchant_trans_id` **prefiks** bilan ajratiladi: bot order → `ord_<id>`, eski oqim → o'zgarmaydi (raqamli pk).

### Texnik asoslar (tekshirildi)
- Egasi: `ProjectModel.owner` (`api/models/project.py`).
- Internal auth: `IsInternalTokenOnly` (`shared/permissions/internal_token.py`) — `X-Internal-Token == settings.INTERNAL_API_TOKEN`, X-User-Id shart emas. Order-create shu bilan himoyalanadi.
- Engine env: release bot `API_URL`, `API_TOKEN`/internal token, `PROJECT_ID` bilan keladi — order-create body'da `project_id` + `payer_chat_id` + `amount` + `comment`.
- `ClickUp(service_id, merchant_id)` + `initializer.generate_pay_link(id=..., amount=..., return_url=...)` — `id` string bo'lishi mumkin (`ord_<pk>`).
- Click webhook: `ClickWebhookAPIView(ClickWebhook)` hooks `successfully_payment(params)`/`cancelled_payment(params)`, `params.merchant_trans_id` bo'yicha. Prefiksga qarab marshrutlanadi.
