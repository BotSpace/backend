package config

import "os"

// Config holds all configuration for the payment service.
type Config struct {
	HTTPPort       string
	DBURL          string
	RedisURL       string
	JWTSecret      string
	StreamGroup    string
	ClickServiceID string
	ClickMerchantID string
	PaymeID        string
	PaymeAPIKey    string
}

// Load reads configuration from environment variables with sensible defaults.
func Load() *Config {
	return &Config{
		HTTPPort:        getEnv("HTTP_PORT", "8083"),
		DBURL:           getEnv("DATABASE_URL", "host=payment-db user=postgres password=2309 dbname=payment_service sslmode=disable"),
		RedisURL:        getEnv("REDIS_URL", "redis://redis:6379"),
		JWTSecret:       getEnv("JWT_SECRET", "secret"),
		StreamGroup:     getEnv("STREAM_GROUP", "payment-group"),
		ClickServiceID:  getEnv("CLICK_SERVICE_ID", ""),
		ClickMerchantID: getEnv("CLICK_MERCHANT_ID", ""),
		PaymeID:         getEnv("PAYME_ID", ""),
		PaymeAPIKey:     getEnv("PAYTECH_API_KEY", ""),
	}
}

func getEnv(key, defaultValue string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultValue
}

// Redis stream / channel constants.
const (
	StreamPaymentEvents  = "payment:events"
	StreamTemplateEvents = "template:events"

	EventPaymentSuccess = "payment_success"
	EventPaymentFailed  = "payment_failed"
	EventOrderCreated   = "order_created"
	EventOrderConfirmed = "order_confirmed"
)
