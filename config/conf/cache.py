from config.env import env

CACHES = {
    "default": {
        "BACKEND": env.str("CACHE_BACKEND"),
        "LOCATION": env.str("REDIS_URL"),
        "TIMEOUT": env.str("CACHE_TIMEOUT"),
    },
}

CACHE_MIDDLEWARE_SECONDS = env("CACHE_TIMEOUT")


CACHEOPS_REDIS = env.str("REDIS_URL")
CACHEOPS_DEFAULTS = {
    "timeout": env.str("CACHE_TIMEOUT"),
}
CACHEOPS = {
    # RelaseModel/DebugModel statuslarini k8s-watcher (alohida Go servis)
    # Postgres'ga TO'G'RIDAN-TO'G'RI yozadi — Django ORM orqali emas, shuning
    # uchun cacheops invalidatsiyasi ishlamaydi. Bu modellarni keshlasak,
    # status deploy'dan keyin 5 daqiqagacha eski "init" holatda ko'rinib qoladi
    # (refresh ham yordam bermaydi). Shuning uchun ularni keshlamaymiz —
    # model-specific profil "api.*" wildcard'idan ustun turadi.
    # ops=() => keshlamaymiz; timeout cacheops uchun integer bo'lishi SHART
    # (default CACHE_TIMEOUT string, shuning uchun bu yerda aniq beramiz).
    "api.relasemodel": {"ops": (), "timeout": 60},
    "api.debugmodel": {"ops": (), "timeout": 60},
    # Token sarfi REAL-TIME bo'lishi shart: report_usage F()-update bilan yozadi,
    # admin panel va agent limit-enforcement (pre_run_remaining) shu jadvalni
    # o'qiydi. 5 daqiqa cache'lansa admin eski son ko'rsatadi va user limitdan
    # oshib ketadi (stale usage). Shuning uchun keshlamaymiz (ops=()).
    "api.usersubscription": {"ops": (), "timeout": 60},
    # !NOTE: api => "you app name"
    "api.*": {
        "ops": "all",  # Barcha turdagi so'rovlarni keshga olish
        "timeout": 60 * 5,  # 5 daqiqa davomida saqlash
    },
    "accounts.*": {
        "ops": "all",  # Barcha turdagi so'rovlarni keshga olish
        "timeout": 60 * 5,  # 5 daqiqa davomida saqlash
    },
    "shared.*": {
        "ops": "all",  # Barcha turdagi so'rovlarni keshga olish
        "timeout": 60 * 5,  # 5 daqiqa davomida saqlash
    },
    "cms.*": {
        "ops": "all",
        "timeout": 60 * 5,
    },
    "template.*": {
        "ops": "all",
        "timeout": 60 * 5,
    },
}
CACHEOPS_DEGRADE_ON_FAILURE = True
CACHEOPS_ENABLED = env.bool("CACHE_ENABLED", False)
