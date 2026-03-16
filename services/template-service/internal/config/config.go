package config

import (
	"log"
	"os"
)

// Config holds all configuration for the template service.
type Config struct {
	HTTPPort    string
	DBURL       string
	RedisURL    string
	JWTSecret   string
	StreamGroup string
}

// Load reads configuration from environment variables with sensible defaults.
// It terminates the process if mandatory secrets are not provided.
func Load() *Config {
	jwtSecret := getEnv("JWT_SECRET", "")
	if jwtSecret == "" {
		log.Fatal("[template] JWT_SECRET environment variable is required")
	}

	dbURL := getEnv("DATABASE_URL", "")
	if dbURL == "" {
		log.Fatal("[template] DATABASE_URL environment variable is required")
	}

	return &Config{
		HTTPPort:    getEnv("HTTP_PORT", "8082"),
		DBURL:       dbURL,
		RedisURL:    getEnv("REDIS_URL", "redis://redis:6379"),
		JWTSecret:   jwtSecret,
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
