package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/botspace/payment-service/internal/config"
	"github.com/botspace/payment-service/internal/handlers"
	"github.com/botspace/payment-service/internal/repository"
	"github.com/botspace/payment-service/internal/streams"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func main() {
	cfg := config.Load()

	// ---- PostgreSQL ----
	db, err := gorm.Open(postgres.Open(cfg.DBURL), &gorm.Config{})
	if err != nil {
		log.Fatalf("[payment] failed to connect to PostgreSQL: %v", err)
	}
	log.Println("[payment] connected to PostgreSQL")

	if err := repository.AutoMigrate(db); err != nil {
		log.Fatalf("[payment] migration failed: %v", err)
	}
	log.Println("[payment] database migrated")

	repo := repository.New(db)

	// ---- Redis ----
	redisOpts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatalf("[payment] invalid REDIS_URL: %v", err)
	}
	redisClient := redis.NewClient(redisOpts)
	if err := redisClient.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("[payment] Redis ping failed: %v", err)
	}
	log.Println("[payment] connected to Redis")
	defer redisClient.Close()

	producer := streams.NewProducer(redisClient)
	consumer := streams.NewConsumer(redisClient, repo, producer, cfg.StreamGroup, "payment-consumer-1")

	consumer.EnsureGroups(context.Background())

	consumeCtx, consumeCancel := context.WithCancel(context.Background())
	defer consumeCancel()
	go consumer.StartConsuming(consumeCtx)

	// ---- HTTP server ----
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(gin.Logger())

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "payment"})
	})

	// Authenticated routes
	auth := router.Group("/api/v1", handlers.AuthMiddleware(cfg))
	{
		txnHandler := handlers.NewTransactionHandler(repo)
		auth.GET("/transaction", txnHandler.List)
		auth.GET("/transaction/:id", txnHandler.Get)

		histHandler := handlers.NewHistoryHandler(repo)
		auth.GET("/history", histHandler.List)
		auth.GET("/history/:id", histHandler.Get)

		payHandler := handlers.NewPaymentLinkHandler(repo, cfg, producer)
		auth.POST("/payment/create-transaction", payHandler.Create)
	}

	// Webhook routes (no auth – signed by payment gateway)
	webhooks := router.Group("/api/v1/payment")
	{
		clickHandler := handlers.NewClickWebhookHandler(repo, producer)
		webhooks.POST("/click/update", clickHandler.Update)

		paymeHandler := handlers.NewPaymeWebhookHandler(repo, producer)
		webhooks.POST("/payme/update", paymeHandler.Update)
	}

	srv := &http.Server{
		Addr:         ":" + cfg.HTTPPort,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("[payment] HTTP server listening on :%s", cfg.HTTPPort)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[payment] server error: %v", err)
		}
	}()

	<-quit
	log.Println("[payment] shutting down...")
	consumeCancel()

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("[payment] server forced to shutdown: %v", err)
	}
	log.Println("[payment] exited")
}
