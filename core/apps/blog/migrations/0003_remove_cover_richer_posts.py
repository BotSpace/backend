"""cover_image maydonini olib tashlaydi va 5 demo postni boyroq, real
prod kontent bilan qayta yozadi (slug bo'yicha update — idempotent).
"""

from django.db import migrations, models


POST_1 = """\
# BotSpace bilan birinchi Telegram botingizni yarating

BotSpace — Telegram botlarini **kod yozmasdan** yaratish uchun vizual platforma.
Bu qo'llanmada hech qanday dasturlash tajribasiz, 10 daqiqada to'liq ishlaydigan
bot yaratamiz: ro'yxatdan o'tkazishdan tortib jonli ishga tushirishgacha.

## 1-qadam. Telegramda botni ro'yxatdan o'tkazish

Har bir Telegram bot Telegramning rasmiy [@BotFather](https://t.me/BotFather)
boti orqali yaratiladi:

1. Telegramda **@BotFather** ni oching va `/newbot` buyrug'ini yuboring.
2. Botga **ko'rinadigan nom** bering (masalan, "Mening Do'konim").
3. Keyin **username** bering — u `bot` bilan tugashi shart (masalan, `mening_dokon_bot`).
4. BotFather sizga **token** beradi — quyidagiga o'xshash uzun matn:

```
7123456789:AAEhBP0z3xY7kQwErTyUiOpAsDfGhJkLmNo
```

> ⚠️ Token — botingizning paroli. Uni hech kimga bermang va ochiq joyga
> joylashtirmang. Tashqariga chiqib ketsa, BotFather'dan `/revoke` orqali
> yangilang.

## 2-qadam. BotSpace'da loyiha ochish

1. [botspace.uz](https://botspace.uz) ga kiring (Telegram orqali bir bosishda kirasiz).
2. **Yangi bot** tugmasini bosing.
3. **Token** maydoniga BotFather bergan tokenni joylashtiring.
4. Tizim tokenni tekshiradi va botingizni avtomatik ulaydi.

Endi loyihangiz tayyor — vizual konstruktor ochiladi.

## 3-qadam. Birinchi oqimni qurish

Eng oddiy bot — foydalanuvchi `/start` bosganda salomlashadigan bot:

1. **Trigger** tugunini qo'shing → turini `/start` buyrug'i qilib belgilang.
2. **Send message** tugunini qo'shing → matn: `Assalomu alaykum! 👋 Botimizga xush kelibsiz.`
3. Ikki tugunni bir-biriga **ulang** (chiziq tortib).

Sxema shunday ko'rinadi:

```
[/start trigger]  →  [Send message: "Assalomu alaykum!"]
```

## 4-qadam. Tugmalar qo'shish

Foydalanuvchiga tanlov berish uchun xabarga **inline tugmalar** qo'shamiz:

- "📦 Mahsulotlar" tugmasi → mahsulotlar ro'yxatini ko'rsatadigan tugunga
- "📞 Aloqa" tugmasi → telefon raqamini so'raydigan tugunga

Har bir tugma alohida tarmoqqa ulanadi, shunda bot foydalanuvchi tanloviga
qarab turlicha javob beradi.

## 5-qadam. Sinab ko'rish va ishga tushirish

1. **Simulyatsiya** (test) rejimida oqimni sinab ko'ring — haqiqiy botga
   teginmasdan, ekranda qanday ishlashini tekshirasiz.
2. Hammasi joyida bo'lsa **Deploy** tugmasini bosing.
3. Bir necha soniyada botingiz **jonli** ishga tushadi.

Telegramda botingizni oching, `/start` yozing — javobini darhol olasiz. 🎉

## Keyingi qadamlar

- [Vizual konstruktorni chuqurroq o'rganing](/blog/vizual-konstruktor-nodes-tugmalar-oqimlar)
- [AI agent bilan tabiiy til orqali bot quring](/blog/ai-agent-mcp-tabiiy-til-bilan-bot)
- [CMS bilan ma'lumot saqlashni o'rganing](/blog/cms-kolleksiyalar-bilan-malumot-saqlash)
"""


POST_2 = """\
# Vizual konstruktor: nodes, tugmalar va oqimlar

BotSpace'ning yuragi — **vizual konstruktor**. Bu yerda botingiz mantig'ini
**tugunlar (nodes)** va ular orasidagi **bog'lanishlar** orqali quryapsiz —
xuddi blok-sxema chizgandek. Bu maqolada barcha asosiy elementlarni ko'rib chiqamiz.

## Tugun (node) nima?

Tugun — botingiz bajaradigan bitta amal. Har bir tugunning **kirishi** (qaysi
tugundan keldi) va **chiqishi** (keyin qaysi tugunga boradi) bor. Tugunlarni
ulab, to'liq stsenariy hosil qilasiz.

## Asosiy tugun turlari

| Tugun | Vazifasi |
|-------|----------|
| **Trigger** | Oqimni ishga tushiradi: `/start`, matn, tugma bosilishi, callback |
| **Send message** | Foydalanuvchiga matn, rasm, video yoki fayl yuboradi |
| **Ask** | Foydalanuvchidan ma'lumot so'raydi (matn, kontakt, lokatsiya) |
| **If condition** | Shartga qarab oqimni ikki yo'lga ajratadi |
| **HTTP request** | Tashqi API bilan ma'lumot almashadi |
| **Custom code** | O'z JavaScript kodingizni ishga tushiradi |
| **AI agent** | Tabiiy tilda javob beradigan aqlli tugun |

## Tugmalar (keyboards)

Xabarlarga ikki xil tugma qo'shish mumkin:

- **Inline tugmalar** — xabarning ostida chiqadi, bosilganda oqim ichida harakat qiladi.
- **Reply tugmalar** — klaviatura o'rnida chiqadi, doimiy menyu sifatida ishlaydi.

Har bir tugma alohida tarmoqqa ulanadi:

```
[Menyu xabari]
   ├── "📦 Mahsulotlar"  →  [Mahsulotlar ro'yxati]
   ├── "🛒 Savatcha"     →  [Savatchani ko'rsatish]
   └── "📞 Aloqa"        →  [Operator bilan bog'lash]
```

## Oqimlar (flows)

Bir nechta tugunni ketma-ket ulab, to'liq stsenariy hosil qilasiz. Misol —
oddiy buyurtma oqimi:

```
/start → Salomlashish → Menyu
                          └── "Buyurtma" → Mahsulotni so'rash
                                            → Miqdorni so'rash
                                            → Manzilni so'rash
                                            → Tasdiqlash → Saqlash
```

## State (holat) — ko'p bosqichli oqimlar

`State` tugunlari foydalanuvchining qaysi bosqichda ekanini **eslab qoladi**.
Bu ko'p bosqichli formalar uchun juda muhim: bot foydalanuvchidan ism so'raydi,
javobni saqlaydi, keyin telefon so'raydi va hokazo — adashmasdan.

Saqlangan qiymatlarga keyingi tugunlarda `{{state_ism}}` ko'rinishida murojaat
qilasiz.

## Shartli mantiq (If condition)

`If` tuguni qiymatni tekshirib, oqimni tarmoqlaydi. Masalan:

- Agar foydalanuvchi yoshi 18 dan katta bo'lsa → asosiy menyu
- Aks holda → "Kechirasiz, xizmat 18+ uchun" xabari

## O'zgaruvchilar (variables)

Oqim davomida to'plangan ma'lumotlarni `{{o'zgaruvchi}}` sintaksisi bilan
ishlatasiz:

- `{{user_first_name}}` — foydalanuvchi ismi
- `{{state_telefon}}` — saqlangan telefon
- `{{collection_mahsulotlar.0.nom}}` — kolleksiyadan olingan qiymat

## Eng yaxshi amaliyotlar

1. **Kichik bloklar** — oqimni katta bitta zanjir emas, kichik qayta
   ishlatiladigan qismlarga bo'ling.
2. **Har doim sinang** — `flow_simulate` orqali deploy'dan oldin tekshiring.
3. **Aniq tugma matnlari** — foydalanuvchi nima bo'lishini tushunsin.
4. **Xatolarni hisobga oling** — noto'g'ri kiritish uchun alohida tarmoq qiling.

Vizual konstruktorni o'zlashtirsangiz, deyarli har qanday botni qura olasiz.
"""


POST_3 = """\
# AI agent va MCP orqali tabiiy til bilan bot yaratish

BotSpace'da botni nafaqat qo'lda tugunlardan yig'ish, balki **tabiiy til**
orqali ham qurishingiz mumkin. Buning uchun **AI agent** va **MCP (Model
Context Protocol)** ishlatiladi. Bu botingizni aqlli yordamchiga aylantiradi.

## AI agent nima?

AI agent — botingiz ichidagi aqlli tugun. U foydalanuvchi xabarini **tushunadi**,
kerak bo'lsa **vositalarni (tool)** chaqiradi va tabiiy javob qaytaradi —
oldindan yozilgan stsenariyga bog'lanib qolmaydi.

Masalan, foydalanuvchi "menga eng arzon telefon kerak" deb yozsa, agent buni
tushunib, mahsulotlar bazasidan qidiradi va mos variantni taklif qiladi.

## Qo'llab-quvvatlanadigan modellar

- **OpenAI** (GPT) — kuchli umumiy model
- **Anthropic (Claude)** — uzun kontekst, aniq ko'rsatma bajarish
- **Google Gemini** — tez va arzon
- **Ollama** — lokal, internetga bog'liq emas (maxfiylik muhim bo'lsa)

## Vositalar (tools)

Agentga turli vositalarni ulashingiz mumkin — shunda u faqat gapirib qolmay,
**amal ham qiladi**:

- **Collection tool** — CMS kolleksiyalaridan o'qish/yozish (mahsulotlar, mijozlar)
- **HTTP tool** — tashqi API chaqirish (yetkazib berish narxi, ob-havo, kurs)
- **Knowledge tool** — bilimlar bazasidan qidirish (FAQ, hujjatlar)
- **Custom code tool** — o'z funksiyangizni bajarish

## MCP — tabiiy til bilan qurish

MCP orqali siz botni **yozma ko'rsatma** bilan quryapsiz. Shunchaki yozasiz:

> "Foydalanuvchidan ismini so'ra, keyin uni `clients` kolleksiyasiga saqla va
> 'Rahmat, {{ism}}!' deb javob ber."

Agent buni tushunib, mos tugunlarni **avtomatik yaratadi**. Bu botni qurishni
bir necha barobar tezlashtiradi — ayniqsa murakkab oqimlarda.

## System prompt — agentning "shaxsi"

Agentga **system prompt** orqali qanday gapirishini va nima qila olishini
aytasiz. Yaxshi misol:

```
Sen "TechStore" onlayn do'koni yordamchisisan.
- Faqat do'kondagi mahsulotlar haqida gapir.
- Narxlarni har doim collection tool orqali tekshir.
- Muloyim va qisqa javob ber, emoji ishlat.
- Buyurtmani faqat tasdiqlangach saqla.
```

## Amaliy maslahatlar

1. **Aniq system prompt** bering — agent chegaralarni bilsin.
2. **Faqat zarur tool'larni** ulang — ortiqchasi modelni chalg'itadi.
3. **Sinab ko'ring** — `flow_simulate` bilan turli savollarni tekshiring.
4. **Token sarfini kuzating** — har bir suhbat token sarflaydi (Billing bo'limida ko'rinadi).
5. **Knowledge tool** ga aniq, qisqa hujjatlar bering — uzun matn aniqlikni kamaytiradi.

## Qachon AI agent ishlatish kerak?

- ✅ FAQ, qo'llab-quvvatlash, mahsulot maslahati
- ✅ Erkin matnli savollar (foydalanuvchi turlicha yozadi)
- ✅ Murakkab, tармоqlanadigan suhbatlar
- ❌ Qat'iy, bir xil oqim (oddiy tugunlar arzonroq va ishonchliroq)

AI agent sodda FAQ botdan tortib to'laqonli savdo yordamchisigacha — hammasiga yaraydi.
"""


POST_4 = """\
# CMS va kolleksiyalar bilan ma'lumot saqlash

Har qanday jiddiy botga ma'lumotni **saqlash** kerak: foydalanuvchilar,
buyurtmalar, mahsulotlar, arizalar. BotSpace buni o'rnatilgan **CMS**
(MongoDB asosida) orqali hal qiladi — alohida baza sozlash shart emas.

## Kolleksiya nima?

Kolleksiya — bu **hujjatlar to'plami** (an'anaviy bazadagi jadval kabi). Har
bir hujjat — JSON ko'rinishidagi yozuv. Masalan, `clients` kolleksiyasidagi
bitta hujjat:

```json
{
  "name": "Ali Valiyev",
  "phone": "+998901234567",
  "city": "Toshkent",
  "created_at": "2026-06-10"
}
```

## Kolleksiya yaratish

1. Loyihangizda **CMS** bo'limiga kiring.
2. **Yangi kolleksiya** tugmasini bosing va nom bering (masalan, `orders`).
3. **Maydonlarni** (field) belgilang va turini tanlang:
   - `text` — matn (ism, manzil)
   - `number` — raqam (narx, miqdor)
   - `boolean` — ha/yo'q (to'langan?)
   - `date` — sana

## Oqimdan yozish va o'qish

Vizual konstruktorda **Collection** tuguni orqali to'rtta asosiy amal bor:

- **insert** — yangi hujjat qo'shish
- **find** — shartga mos hujjatlarni topish
- **update** — mavjud hujjatni yangilash
- **delete** — o'chirish

Misol: foydalanuvchidan olingan ma'lumotni saqlash —

```
Ism so'rash → Telefon so'rash → [insert: clients]
   {name: {{state_ism}}, phone: {{state_telefon}}}
```

## Filtrlash (find)

`find` amalida shart yozasiz. Masalan, faqat Toshkentdagi mijozlar:

```json
{ "city": "Toshkent" }
```

Yoki narxi 100 000 dan yuqori mahsulotlar:

```json
{ "price": { "$gte": 100000 } }
```

## Misol: oddiy CRM bot

1. Foydalanuvchidan ism va telefon so'raysiz.
2. `clients` kolleksiyasiga `insert` qilasiz.
3. Admin botga `/clients` yozsa, `find` orqali ro'yxatni ko'rsatasiz.
4. Har bir mijozni `update` orqali "qo'ng'iroq qilindi" deb belgilaysiz.

## AI agent + CMS

AI agentga **Collection tool** ulasangiz, u kolleksiyadan o'zi o'qiy oladi.
Masalan, "qaysi mahsulotlar omborda bor?" degan savolga agent `products`
kolleksiyasidan real javob beradi.

## Maslahatlar

1. **Indeks qo'shing** — tez-tez qidiriladigan maydonlarga (telefon, slug)
   indeks qo'ying, so'rovlar tezlashadi.
2. **Maydon nomlarini izchil** tuting — `phone` yoki `phone_number`, ikkalasini
   aralashtirmang.
3. **Sana va summalarni to'g'ri turda** saqlang — keyin filtrlash oson bo'ladi.
4. **Maxfiy ma'lumotni** ehtiyot bilan saqlang — kerak bo'lmasa, saqlamang.

CMS sizning botingizni oddiy javob beruvchidan **to'laqonli ilovaga** aylantiradi.
"""


POST_5 = """\
# To'lovlar va botdan daromad olish

Bot orqali mahsulot yoki xizmat sotyapsizmi? BotSpace **to'lovlarni** to'g'ridan-
to'g'ri oqimga integratsiya qilish imkonini beradi — foydalanuvchi botdan
chiqmasdan to'lov qiladi, siz esa daromadni boshqarasiz.

## Qo'llab-quvvatlanadigan usullar

- **Click** — O'zbekistondagi keng tarqalgan to'lov tizimi
- **Payme** — mashhur to'lov ilovasi
- **Telegram invoice** — Telegram ichidagi to'lov

## To'lov oqimi qanday ishlaydi

```
Buyurtma  →  Summani hisoblash  →  To'lov havolasi yaratish
          →  Foydalanuvchi to'laydi  →  Webhook tasdiqlaydi  →  Oqim davom etadi
```

1. **Summani hisoblang** — buyurtma narxini o'zgaruvchiga yozasiz.
2. **To'lov tuguni** havola yaratadi va foydalanuvchiga yuboradi.
3. Foydalanuvchi havola orqali to'laydi.
4. To'lov tizimi **webhook** orqali botga "to'landi" deb xabar beradi.
5. Oqim avtomatik davom etadi — chek yuboriladi, buyurtma "to'langan" deb belgilanadi.

## Buyurtmani saqlash

To'lovdan **oldin** buyurtmani CMS'ga saqlang (`pending` holatida), to'lov
tasdiqlanganda `paid` ga o'zgartiring:

```
[insert: orders]
  { items: {{savat}}, total: {{summa}}, status: "pending" }
→ To'lov havolasi
→ (webhook) → [update: orders] { status: "paid" }
```

## Muvaffaqiyatsiz to'lovlar

Har doim **muvaffaqiyatsiz** holat uchun alohida tarmoq qiling:

- To'lov bekor qilindi → "To'lov amalga oshmadi, qayta urinib ko'ring" + tugma
- Vaqt tugadi → buyurtmani `cancelled` ga o'tkazing

## Daromadni boshqarish

Botingiz orqali tushgan pul **balansingizga** to'planadi. Uni boshqarish:

- **Dashboard** — botlardan tushgan daromad statistikasini real vaqtda ko'rasiz.
- **Earnings** — har bir bot bo'yicha tushum va tranzaksiyalar tarixi.
- **Withdrawal** — mablag'ni kartangizga yechib olasiz.

## Pul yechish (withdrawal)

1. **Verifikatsiya (KYC)** dan o'ting — pasport va shaxsni tasdiqlovchi rasm.
2. **Withdrawal** bo'limida summa va karta raqamini kiriting.
3. So'rov adminlar tomonidan tekshirilib, kartangizga o'tkaziladi.

> Eslatma: faqat **botlardan tushgan daromad** yechiladi, o'zingiz to'ldirgan
> balans emas.

## Maslahatlar

1. To'lovdan oldin buyurtmani CMS'ga saqlang — webhook kechiksa ham ma'lumot yo'qolmaydi.
2. Foydalanuvchiga **doim aniq tasdiq** xabarini yuboring (chek, buyurtma raqami).
3. Narxlarni kolleksiyada saqlang — kodga qotirib qo'ymang.
4. Test rejimida to'lovni sinab ko'ring, keyin prodga chiqaring.

To'lovlarni sozlagach, botingiz haqiqiy **biznes vositasiga** aylanadi. 💰
"""


UPDATED = {
    "botspace-bilan-birinchi-telegram-bot": {
        "excerpt": "BotFather'dan deploy'gacha — birinchi ishlaydigan botingizni 10 daqiqada, kod yozmasdan ishga tushiring.",
        "content": POST_1,
    },
    "vizual-konstruktor-nodes-tugmalar-oqimlar": {
        "excerpt": "Tugunlar, tugmalar, holat va shartli mantiq — vizual konstruktorning barcha asosiy elementlari bir maqolada.",
        "content": POST_2,
    },
    "ai-agent-mcp-tabiiy-til-bilan-bot": {
        "excerpt": "AI agent, vositalar, system prompt va MCP orqali botni tabiiy til bilan qanday qurish — amaliy misollar bilan.",
        "content": POST_3,
    },
    "cms-kolleksiyalar-bilan-malumot-saqlash": {
        "excerpt": "MongoDB asosidagi CMS, kolleksiyalar, CRUD amallari va filtrlash — botingizga to'laqonli ma'lumotlar bazasi.",
        "content": POST_4,
    },
    "tolovlar-va-botdan-daromad-olish": {
        "excerpt": "Click, Payme va Telegram to'lovlarini oqimga ulang; daromad, withdrawal va KYC jarayonini o'rganing.",
        "content": POST_5,
    },
}


def update_posts(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPostModel")
    for slug, data in UPDATED.items():
        BlogPost.objects.filter(slug=slug).update(
            excerpt=data["excerpt"],
            content=data["content"],
        )


def noop(apps, schema_editor):
    # Kontent yangilanishini orqaga qaytarmaymiz (eski matn saqlanmagan).
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0002_seed_demo_posts"),
    ]

    operations = [
        migrations.RemoveField(model_name="blogpostmodel", name="cover_image"),
        migrations.RunPython(update_posts, noop),
    ]
