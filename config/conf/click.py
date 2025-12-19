from config.env import env

CLICK_SERVICE_ID = env.str("CLICK_SERVICE_ID")
CLICK_MERCHANT_ID = env.str("CLICK_MERCHANT_ID")
CLICK_SECRET_KEY = env.str("CLICK_SECRET_KEY")
CLICK_ACCOUNT_MODEL = "core.apps.payment.models.TransactionModel"
CLICK_AMOUNT_FIELD = "amount"

# CLICK_COMMISSION_PERCENT = "(optional int field) your companies comission percent if applicable"
CLICK_DISABLE_ADMIN = False
