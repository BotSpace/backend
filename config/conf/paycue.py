from config.env import env

# Paycue — Humo-karta to'lov avtomatizatsiyasi (https://github.com/UzStack/paycue).
# Gateway emas: `POST {base}/create/transaction/` moslashtirilgan summa qaytaradi,
# foydalanuvchi aniq o'sha summani Humo kartaga o'tkazadi, paycue webhook bilan
# tasdiqlaydi.
PAYCUE_BASE_URL = env.str("PAYCUE_BASE_URL", default="https://paycue.iprogrammer.uz")
# Transaction YARATISHDA paycue'ga X-API-Key sifatida yuboriladigan kalit
# (outgoing — paycue /create/transaction/ ni shu bilan himoyalaydi).
PAYCUE_API_KEY = env.str("PAYCUE_API_KEY", default="")
# Webhook KELGANDA tekshiriladigan kalit (incoming — paycue webhook'ni shu
# X-API-Key bilan yuboradi). Bo'sh bo'lsa PAYCUE_API_KEY ishlatiladi.
PAYCUE_WEBHOOK_KEY = env.str("PAYCUE_WEBHOOK_KEY", default="")
# Foydalanuvchiga ko'rsatiladigan Humo karta raqami (to'lov ko'rsatmasi uchun).
PAYCUE_CARD = env.str("PAYCUE_CARD", default="")
