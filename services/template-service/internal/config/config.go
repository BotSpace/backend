package config

import "os"

// Config holds all configuration for the template service.
type Config struct {
	HTTPPort    string
	DBURL       string
	RedisURL    string
	JWTSecret   string
	StreamGroup string
}

// Load reads configuration from environment variables with sensible defaults.
func Load() *Config {
	return &Config{
		HTTPPort:    getEnv("HTTP_PORT", "8082"),
		DBURL:       getEnv("DATABASE_URL", "host=template-db user=postgres password=2309 dbname=template_service sslmode=disable"),
		RedisURL:    getEnv("REDIS_URL", "redis://redis:6379"),
		JWTSecret:   getEnv("JWT_SECRET", "secret"),
		StreamGroup: getEnv("STREAM_GROUP", "template-group"),
	}
}

func getEnv(key, defaultValue string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return defaultValue
}

// Redis stream / channel constants shared across all services.
const (
	StreamPaymentEvents  = "payment:events"
	StreamTemplateEvents = "template:events"

	EventPaymentSuccess = "payment_success"
	EventPaymentFailed  = "payment_failed"
	EventOrderCreated   = "order_created"
	EventOrderConfirmed = "order_confirmed"
)
