package config

import (
	"os"
)

// Config holds all configuration for the CMS service.
type Config struct {
	HTTPPort    string
	MongoURI    string
	MongoDB     string
	RedisURL    string
	JWTSecret   string
	StreamGroup string
}

// Load reads configuration from environment variables with sensible defaults.
func Load() *Config {
	return &Config{
		HTTPPort:    getEnv("HTTP_PORT", "8081"),
		MongoURI:    getEnv("MONGO_URI", "mongodb://admin:admin123@mongo:27017"),
		MongoDB:     getEnv("MONGO_DB", "cms_service"),
		RedisURL:    getEnv("REDIS_URL", "redis://redis:6379"),
		JWTSecret:   getEnv("JWT_SECRET", "secret"),
		StreamGroup: getEnv("STREAM_GROUP", "cms-group"),
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
	StreamCMSEvents      = "cms:events"

	EventPaymentSuccess = "payment_success"
	EventPaymentFailed  = "payment_failed"
	EventOrderCreated   = "order_created"
	EventOrderConfirmed = "order_confirmed"
	EventCollectionCreated = "collection_created"
	EventCollectionDeleted = "collection_deleted"
)
