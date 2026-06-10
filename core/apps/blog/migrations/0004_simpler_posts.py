"""5 demo postni oddiy (texnik bo'lmagan) foydalanuvchilar uchun qayta yozadi.

Kod bloklari, JSON, texnik atamalar olib tashlandi — sodda, tushunarli til.
Idempotent: slug bo'yicha update qiladi.
"""

from django.db import migrations


POST_1 = """\
# BotSpace bilan birinchi botingizni yarating

Telegram bot — bu sizning o'rningizga 24 soat ishlaydigan yordamchi. U
mijozlarga javob beradi, buyurtma qabul qiladi, ma'lumot beradi — siz uxlab
yotganingizda ham. Eng yaxshisi: buni yaratish uchun dasturchi bo'lish shart emas.

## Botingiz nima qila oladi?

- Mijozlarning savollariga avtomatik javob beradi
- Buyurtma va arizalarni qabul qiladi
- Narx, manzil, ish vaqti kabi ma'lumotlarni ko'rsatadi
- Yangiliklarni barcha obunachilarga bir tugma bilan yuboradi

## Qanday boshlash kerak?

**1. Telegramda bot oching.**
Telegramdagi maxsus "BotFather" yordamchisiga yozasiz, botingizga nom berasiz —
va u sizga maxsus kalit (token) beradi. Bu kalit — botingizning "pasporti".

**2. BotSpace'ga kiring.**
botspace.uz saytiga kiring, "Yangi bot" tugmasini bosing va o'sha kalitni
joylashtiring. Tamom — botingiz tizimga ulandi.

**3. Botingizni "qurib" oling.**
Maxsus oynada siz botingiz nima deyishini va qanday javob berishini
belgilaysiz — xuddi rasm chizgandek, bloklarni bir-biriga ulab.

**4. Ishga tushiring.**
"Deploy" tugmasini bosasiz va botingiz bir necha soniyada jonli ishlaydi.
Telegramda uni ochib, sinab ko'rishingiz mumkin.

## Maslahat

Boshida murakkab qilmang. Avval oddiy bot yarating: salomlashsin va asosiy
menyuni ko'rsatsin. Keyin asta-sekin yangi imkoniyatlar qo'shib borasiz.

Tayyormisiz? Birinchi botingizni bugun yaratib ko'ring — bu o'ylaganingizdan
ham oson.
"""


POST_2 = """\
# Botingizni qanday "qurish" kerak?

BotSpace'da bot yaratish — konstruktor o'yinchog'ini yig'ishga o'xshaydi. Siz
tayyor bloklarni bir-biriga ulab, botingiz qanday ishlashini belgilaysiz. Kod
yozish shart emas — hammasi ko'z bilan ko'rinadi.

## Asosiy g'oya

Har bir blok — botingiz bajaradigan bitta ish:

- **Salomlashish** — foydalanuvchi botga kirganda nima deyishi
- **Xabar yuborish** — matn, rasm yoki video ko'rsatish
- **Savol berish** — foydalanuvchidan ism, telefon yoki manzil so'rash
- **Tugmalar** — tanlov tugmalarini ko'rsatish

Bloklarni chiziq bilan ulab, to'liq suhbatni hosil qilasiz.

## Tugmalar bilan boshqarish

Foydalanuvchiga uzun matn yozdirish o'rniga, tayyor **tugmalar** bering. Masalan,
asosiy menyuda:

- "Mahsulotlar"
- "Buyurtma berish"
- "Biz bilan bog'lanish"

Har bir tugma o'z yo'nalishiga olib boradi. Foydalanuvchi adashmaydi va botdan
foydalanish oson bo'ladi.

## Bot eslab qoladi

Botingiz suhbat davomida foydalanuvchi aytgan narsalarni eslab qoladi. Masalan,
avval ismini so'raydi, keyin telefonini — va oxirida hammasini birga ko'rsatib,
buyurtmani tasdiqlaydi. Foydalanuvchi o'zini xuddi haqiqiy odam bilan
gaplashayotgandek his qiladi.

## Maslahatlar

1. Suhbatni qisqa va aniq qiling — ortiqcha bosqichlar foydalanuvchini charchatadi.
2. Tugmalarga tushunarli nom bering.
3. Ishga tushirishdan oldin botni o'zingiz sinab ko'ring.

Bir marta urinib ko'rsangiz, qolganini o'zingiz bemalol qila olasiz.
"""


POST_3 = """\
# Botingizga sun'iy intellekt qo'shing

Oddiy bot faqat siz oldindan yozgan javoblarni beradi. Lekin **sun'iy
intellekt (AI)** qo'shsangiz, botingiz odamning savolini tushunadi va o'zi mos
javob topadi — xuddi tirik maslahatchi kabi.

## Bu nimaga kerak?

Foydalanuvchilar savolni har xil yozadi. Kimdir "telefon bormi?", kimdir "eng
arzon telefoningiz qancha turadi?" deydi. Oddiy bot bularning hammasiga
tayyorlanib bo'lmaydi. AI esa savolning **ma'nosini** tushunadi va to'g'ri
javob beradi.

## AI botingiz uchun nima qila oladi?

- Mijozning savoliga tabiiy, jonli til bilan javob beradi
- Mahsulotlaringizdan keraklisini topib beradi
- Tez-tez so'raladigan savollarga charchamasdan javob qaytaradi
- Mijozni to'g'ri bo'limga yo'naltiradi

## Sozlash juda oson

Siz AI'ga oddiy so'zlar bilan vazifa berasiz. Masalan:

"Sen do'konimizning yordamchisisan. Faqat bizning mahsulotlar haqida gapir,
muloyim bo'l va qisqa javob ber."

Shu yetarli — AI shu ko'rsatmaga amal qiladi.

## Tabiiy til bilan bot yaratish

Eng qizig'i: botingizni ham oddiy so'zlar bilan qura olasiz. Siz shunchaki
yozasiz — "foydalanuvchidan ismini so'ra va saqlab qo'y" — tizim esa kerakli
qismlarni o'zi tayyorlaydi. Bu vaqtingizni ancha tejaydi.

## Maslahat

AI'ga aniq vazifa bering — u nima qilishi va nima qilmasligini bilsin. Qancha
aniq aytsangiz, javoblar shuncha yaxshi bo'ladi.

Sun'iy intellekt botingizni oddiy javob beruvchidan haqiqiy yordamchiga
aylantiradi.
"""


POST_4 = """\
# Botingiz ma'lumotni eslab qolsin

Jiddiy bot uchun ma'lumotni saqlash zarur: mijozlar, buyurtmalar, mahsulotlar.
Aks holda har safar hammasi boshidan boshlanadi. BotSpace'da botingiz uchun
o'rnatilgan "daftar" bor — hech narsa sozlash shart emas.

## Buni qanday tasavvur qilish mumkin?

Bu — Excel jadvaliga o'xshaydi. Har bir jadvalda ustunlar bor (masalan, ism,
telefon, shahar), va har bir mijoz alohida qator bo'lib yoziladi. Botingiz shu
jadvalga yangi qatorlar qo'shadi va keraklisini topadi.

## Nimalarni saqlash mumkin?

- **Mijozlar** — ism, telefon, manzil
- **Buyurtmalar** — nima, qancha, qachon
- **Mahsulotlar** — nomi, narxi, mavjudligi
- **Arizalar** — har qanday so'rovlar

## Botingiz buni qanday ishlatadi?

Misol uchun oddiy do'kon boti:

1. Foydalanuvchidan ism va telefon so'raydi
2. Ularni "Mijozlar" daftariga yozib qo'yadi
3. Keyinroq siz barcha mijozlar ro'yxatini ko'rishingiz mumkin

Yoki mahsulot boti: foydalanuvchi "qanaqa telefonlar bor?" deb so'rasa, bot
daftardan o'qib, ro'yxatni ko'rsatadi.

## Nima foydasi bor?

Saqlangan ma'lumot bilan botingiz haqiqiy biznes vositasiga aylanadi. Siz
mijozlaringizni bilasiz, buyurtmalarni kuzatasiz va hammasi bir joyda tartibli
turadi.

## Maslahat

Faqat haqiqatan kerakli ma'lumotni so'rang. Ortiqcha savollar foydalanuvchini
charchatadi va ba'zilar botdan voz kechadi.
"""


POST_5 = """\
# Bot orqali to'lov qabul qiling

Botingiz orqali mahsulot yoki xizmat sotyapsizmi? Unda to'lovni ham to'g'ridan-
to'g'ri bot ichida qabul qilishingiz mumkin. Mijoz hech qayerga o'tmaydi —
hammasi suhbat davomida bo'ladi.

## Qanday ishlaydi?

1. Mijoz buyurtma beradi
2. Bot unga to'lov uchun havola yuboradi
3. Mijoz qulay usulda (Click, Payme) to'laydi
4. To'lov o'tgach, bot avtomatik tasdiq yuboradi

Mijoz uchun bu juda qulay — bir necha bosishda hammasi tugaydi.

## Sizning foydangiz

- To'lov darhol tasdiqlanadi, qo'lda tekshirish shart emas
- Har bir buyurtma va to'lov saqlanib qoladi
- Mijozlar istalgan vaqtda, hatto kechasi ham to'lay oladi

## Pulni qayerdan olaman?

Botingiz orqali tushgan pul **balansingizga** to'planadi. Siz uni istalgan
vaqtda o'z kartangizga yechib olishingiz mumkin. Dashboard'da qancha pul
tushganini va har bir to'lovni ko'rib turasiz.

Pulni birinchi marta yechishdan oldin bir martalik tasdiqlash (shaxsingizni
tekshirish) bo'ladi — bu xavfsizlik uchun.

## Maslahatlar

1. Mijozga doim aniq tasdiq xabarini yuboring — u to'lovi o'tganiga ishonch hosil qilsin.
2. To'lov o'tmasa, "qayta urinib ko'ring" tugmasini qo'shing.
3. Narxlarni doim yangilab turing.

To'lovni sozlagandan so'ng, botingiz nafaqat gaplashadi, balki **daromad ham
keltiradi**.
"""


UPDATED = {
    "botspace-bilan-birinchi-telegram-bot": {
        "excerpt": "Dasturchi bo'lish shart emas — birinchi botingizni oddiy qadamlar bilan o'zingiz yarating.",
        "content": POST_1,
    },
    "vizual-konstruktor-nodes-tugmalar-oqimlar": {
        "excerpt": "Botingizni konstruktor o'yinchog'idek yig'ing: bloklar, tugmalar va sodda suhbat — kodsiz.",
        "content": POST_2,
    },
    "ai-agent-mcp-tabiiy-til-bilan-bot": {
        "excerpt": "Sun'iy intellekt botingizni odamning savolini tushunadigan jonli yordamchiga aylantiradi.",
        "content": POST_3,
    },
    "cms-kolleksiyalar-bilan-malumot-saqlash": {
        "excerpt": "Mijozlar, buyurtmalar va mahsulotlarni saqlang — botingiz hammasini eslab qolsin.",
        "content": POST_4,
    },
    "tolovlar-va-botdan-daromad-olish": {
        "excerpt": "To'lovni to'g'ridan-to'g'ri bot ichida qabul qiling va daromadingizni kartangizga yeching.",
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
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("blog", "0003_remove_cover_richer_posts"),
    ]

    operations = [
        migrations.RunPython(update_posts, noop),
    ]
