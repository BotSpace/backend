from config.env import env

PAYTECH_API_KEY=env("PAYTECH_API_KEY")
PAYME_ID=env("PAYME_ID")
PAYME_KEY=env("PAYME_KEY")
PAYME_ACCOUNT_FIELD = "order_id"
PAYME_AMOUNT_FIELD = "amount"
PAYME_ACCOUNT_MODEL = "core.apps.payment.models.TransactionModel"
PAYME_ONE_TIME_PAYMENT = True

PAYME_DISABLE_ADMIN = False