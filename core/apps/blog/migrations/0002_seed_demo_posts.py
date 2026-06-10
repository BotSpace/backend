"""5 ta demo blog postini (o'zbek tilida) seed qiladi.

Idempotent: slug bo'yicha tekshiradi, mavjud bo'lsa qayta yaratmaydi.
Migration ``apps.get_model`` orqali ishlaganida custom ``save()`` chaqirilmaydi,
shuning uchun ``slug`` va ``published_at`` ni qo'lda o'rnatamiz.
"""

from django.db import migrations
from django.utils import timezone


POST_1 = """\
# BotSpace bilan birinchi Telegram botingizni yarating

BotSpace — Telegram botlarini kod yozmasdan yaratish uchun vizual platforma.
Ushbu qo'llanmada birinchi botingizni boshdan-oyoq ishga tushiramiz.

## 1. Botni ro'yxatdan o'tkazish

Avval Telegramdagi [@BotFather](https://t.me/BotFather) orqali yangi bot oching:

1. `/newbot` buyrug'ini yuboring
2. Botga nom va `username` bering
3. BotFather bergan **tokenni** nusxalang

## 2. BotSpace'da loyiha ochish

- `botspace.uz` ga kiring va **Yangi loyiha** tugmasini bosing
- Token maydoniga BotFather bergan tokenni joylashtiring
- Loyiha avtomatik ulanadi

## 3. Birinchi oqim

Vizual konstruktorda eng oddiy oqim shunday ko'rinadi:

- **Trigger**: `/start` buyrug'i
- **Send message**: "Assalomu alaykum! 👋"

> Maslahat: har bir tugun (node) ni bir-biriga ulab, mantiqiy oqim hosil qilasiz.

## 4. Ishga tushirish

Tayyor bo'lgach **Deploy** tugmasini bosing — bot bir necha soniyada jonli ishga tushadi.
Endi Telegramda botingizga `/start` yozib, javobini ko'rishingiz mumkin.

Keyingi maqolalarda vizual konstruktor va AI agentlarni chuqurroq o'rganamiz.
"""

POST_2 = """\
# Vizual konstruktor: nodes, tugmalar va oqimlar

BotSpace'ning yuragi — vizual konstruktor. U yerda botingiz mantig'ini
**tugunlar (nodes)** va ular orasidagi **bog'lanishlar** orqali quryapsiz.

## Asosiy tugun turlari

- **Trigger** — oqimni ishga tushiruvchi hodisa (`/start`, matn, tugma bosilishi)
- **Send message** — foydalanuvchiga matn/rasm yuborish
- **Ask** — foydalanuvchidan ma'lumot so'rash (matn, kontakt, lokatsiya)
- **If condition** — shartga qarab oqimni tarmoqlash
- **HTTP request** — tashqi API bilan ishlash

## Tugmalar (keyboards)

Xabarlarga inline tugmalar qo'shib, foydalanuvchini boshqarishingiz mumkin:

- Har bir tugma alohida tarmoqqa ulanadi
- `callback` tugmalari oqim ichidagi keyingi tugunga olib boradi
- URL tugmalari tashqi havolani ochadi

## Oqimlar (flows)

Bir nechta tugunni ketma-ket ulab, to'liq stsenariy hosil qilasiz:

```
/start  →  Salomlashish  →  Menyu tugmalari
                                 ├── "Mahsulotlar" → ro'yxat
                                 └── "Aloqa"       → kontakt so'rash
```

## State (holat)

`State` tugunlari foydalanuvchining qaysi bosqichda ekanini eslab qoladi —
shunda ko'p bosqichli formalar (masalan, buyurtma berish) muammosiz ishlaydi.

> Yaxshi amaliyot: oqimni kichik, qayta ishlatiladigan bloklarga bo'ling.
"""

POST_3 = """\
# AI agent va MCP orqali tabiiy til bilan bot yaratish

BotSpace'da botni nafaqat qo'lda, balki **tabiiy til** orqali ham qurishingiz mumkin.
Buning uchun AI agent va **MCP (Model Context Protocol)** ishlatiladi.

## AI agent nima?

AI agent — botingiz ichidagi aqlli tugun. U foydalanuvchi xabarini tushunadi,
kerakli **tool**'larni chaqiradi va javob qaytaradi.

Qo'llab-quvvatlanadigan provayderlar:

- OpenAI
- Anthropic (Claude)
- Gemini
- Ollama (lokal modellar)

## Tool'lar

Agentga quyidagi vositalarni ulashingiz mumkin:

- **Collection tool** — CMS kolleksiyalaridan ma'lumot o'qish/yozish
- **HTTP tool** — tashqi API chaqirish
- **Knowledge tool** — bilimlar bazasidan qidirish
- **Custom code tool** — o'z funksiyangiz

## MCP bilan tabiiy til

MCP orqali siz shunchaki yozasiz:

> "Foydalanuvchidan ismini so'ra, keyin uni `clients` kolleksiyasiga saqla."

Agent buni tushunib, mos tugunlarni avtomatik yaratadi. Bu botni qurishni
sezilarli darajada tezlashtiradi.

## Maslahatlar

1. Agentga aniq **system prompt** bering
2. Faqat zarur tool'larni ulang — ortiqchasi modelni chalg'itadi
3. Javoblarni `flow_simulate` orqali sinab ko'ring

AI agent sodda FAQ botdan tortib murakkab yordamchigacha — hammasiga yaraydi.
"""

POST_4 = """\
# CMS va kolleksiyalar bilan ma'lumot saqlash

Har qanday jiddiy botga ma'lumotni saqlash kerak: foydalanuvchilar, buyurtmalar,
mahsulotlar. BotSpace buni **CMS** (MongoDB asosida) orqali hal qiladi.

## Kolleksiya nima?

Kolleksiya — bu hujjatlar to'plami (jadval kabi). Masalan, `clients` kolleksiyasi:

```json
{
  "name": "Ali",
  "phone": "+998901234567",
  "created_at": "2026-06-10"
}
```

## Kolleksiya yaratish

- CMS bo'limiga kiring
- **Yangi kolleksiya** tugmasini bosing
- Maydonlarni (field) belgilang: matn, raqam, sana, bool

## Oqimdan yozish va o'qish

Vizual konstruktorda **Collection** tuguni orqali:

- `insert` — yangi hujjat qo'shish
- `find` — shartga mos hujjatlarni topish
- `update` — mavjud hujjatni yangilash
- `delete` — o'chirish

## Misol: oddiy CRM

1. Foydalanuvchidan ism va telefon so'raysiz
2. `clients` kolleksiyasiga `insert` qilasiz
3. Keyinroq admin uchun `find` orqali ro'yxatni ko'rsatasiz

> Maslahat: tez-tez qidiriladigan maydonlarga indeks qo'shing — bu so'rovlarni tezlashtiradi.

CMS sizning botingizni oddiy javob beruvchidan to'laqonli ilovaga aylantiradi.
"""

POST_5 = """\
# To'lovlar va botdan daromad olish

Bot orqali mahsulot yoki xizmat sotyapsizmi? BotSpace **to'lovlarni** to'g'ridan-to'g'ri
oqimga integratsiya qilish imkonini beradi.

## Qo'llab-quvvatlanadigan usullar

- Payme
- Click
- Telegram ichidagi to'lov (invoice)

## To'lov havolasini yaratish

Oqimda to'lov tuguni orqali summa va tavsifni belgilaysiz, tizim esa
foydalanuvchiga **to'lov havolasini** yaratib beradi.

```
Buyurtma  →  Summani hisoblash  →  To'lov havolasi  →  Tasdiqlash
```

## To'lovni tasdiqlash

To'lov muvaffaqiyatli o'tgach:

1. Tizim `webhook` orqali xabar oladi
2. Oqim avtomatik davom etadi
3. Foydalanuvchiga chek/tasdiq yuboriladi

## Daromadni boshqarish

- **Dashboard**'da tushumlar statistikasini kuzating
- **Withdrawal** orqali mablag'ni hisobingizga yeching
- Har bir tranzaksiya tarixini ko'rishingiz mumkin

## Maslahatlar

1. To'lovdan oldin buyurtmani CMS'ga saqlang
2. Muvaffaqiyatsiz to'lovlar uchun alohida tarmoq qiling
3. Foydalanuvchiga doim aniq tasdiq xabarini yuboring

To'lovlarni sozlagach, botingiz haqiqiy biznes vositasiga aylanadi. 💰
"""


DEMO_POSTS = [
    {
        "title": "BotSpace bilan birinchi Telegram botingizni yarating",
        "slug": "botspace-bilan-birinchi-telegram-bot",
        "excerpt": "BotFather'dan tortib to deploy'gacha — birinchi botingizni kod yozmasdan ishga tushiring.",
        "content": POST_1,
    },
    {
        "title": "Vizual konstruktor: nodes, tugmalar va oqimlar",
        "slug": "vizual-konstruktor-nodes-tugmalar-oqimlar",
        "excerpt": "Tugunlar, tugmalar va oqimlar yordamida botingiz mantig'ini vizual quring.",
        "content": POST_2,
    },
    {
        "title": "AI agent va MCP orqali tabiiy til bilan bot yaratish",
        "slug": "ai-agent-mcp-tabiiy-til-bilan-bot",
        "excerpt": "AI agent, tool'lar va MCP orqali botni tabiiy til bilan tezroq quring.",
        "content": POST_3,
    },
    {
        "title": "CMS va kolleksiyalar bilan ma'lumot saqlash",
        "slug": "cms-kolleksiyalar-bilan-malumot-saqlash",
        "excerpt": "MongoDB asosidagi CMS bilan foydalanuvchilar, buyurtmalar va boshqa ma'lumotlarni saqlang.",
        "content": POST_4,
    },
    {
        "title": "To'lovlar va botdan daromad olish",
        "slug": "tolovlar-va-botdan-daromad-olish",
        "excerpt": "Payme, Click va Telegram to'lovlarini oqimga ulab, botingizdan daromad oling.",
        "content": POST_5,
    },
]


def seed_posts(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPostModel")
    now = timezone.now()
    for index, data in enumerate(DEMO_POSTS):
        if BlogPost.objects.filter(slug=data["slug"]).exists():
            continue
        BlogPost.objects.create(
            title=data["title"],
            slug=data["slug"],
            excerpt=data["excerpt"],
            content=data["content"],
            is_published=True,
            published_at=now,
        )


def unseed_posts(apps, schema_editor):
    BlogPost = apps.get_model("blog", "BlogPostModel")
    slugs = [data["slug"] for data in DEMO_POSTS]
    BlogPost.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_posts, unseed_posts),
    ]
