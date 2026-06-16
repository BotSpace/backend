from config.env import env

# Paycue — Humo-karta to'lov avtomatizatsiyasi (https://github.com/UzStack/paycue).
# Gateway emas: `POST {base}/create/transaction/` moslashtirilgan summa qaytaradi,
# foydalanuvchi aniq o'sha summani Humo kartaga o'tkazadi, paycue webhook bilan
# tasdiqlaydi.
PAYCUE_BASE_URL = env.str("PAYCUE_BASE_URL", default="https://paycue.iprogrammer.uz")
# Basic Auth API key (paycue .env'dagi kalit).
PAYCUE_API_KEY = env.str("PAYCUE_API_KEY", default="")
# Foydalanuvchiga ko'rsatiladigan Humo karta raqami (to'lov ko'rsatmasi uchun).
PAYCUE_CARD = env.str("PAYCUE_CARD", default="")
