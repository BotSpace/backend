package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/botspace/template-service/internal/config"
	"github.com/botspace/template-service/internal/handlers"
	"github.com/botspace/template-service/internal/repository"
	"github.com/botspace/template-service/internal/streams"
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
		log.Fatalf("[template] failed to connect to PostgreSQL: %v", err)
	}
	log.Println("[template] connected to PostgreSQL")

	if err := repository.AutoMigrate(db); err != nil {
		log.Fatalf("[template] migration failed: %v", err)
	}
	log.Println("[template] database migrated")

	repo := repository.New(db)

	// ---- Redis ----
	redisOpts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatalf("[template] invalid REDIS_URL: %v", err)
	}
	redisClient := redis.NewClient(redisOpts)
	if err := redisClient.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("[template] Redis ping failed: %v", err)
	}
	log.Println("[template] connected to Redis")
	defer redisClient.Close()

	producer := streams.NewProducer(redisClient)
	consumer := streams.NewConsumer(redisClient, repo, producer, cfg.StreamGroup, "template-consumer-1")

	consumer.EnsureGroups(context.Background())

	consumeCtx, consumeCancel := context.WithCancel(context.Background())
	defer consumeCancel()
	go consumer.StartConsuming(consumeCtx)

	// ---- HTTP server ----
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(gin.Logger())

	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "template"})
	})

	// Public routes
	public := router.Group("/api/v1/template")
	{
		th := handlers.NewTemplateHandler(repo)
		public.GET("/list", th.List)
		public.GET("/list/:slug", th.Get)

		ch := handlers.NewCategoryHandler(repo)
		public.GET("/category", ch.List)

		fh := handlers.NewFeatureHandler(repo)
		public.GET("/feature", fh.List)
	}

	// Authenticated routes
	auth := router.Group("/api/v1/template", handlers.AuthMiddleware(cfg))
	{
		uth := handlers.NewUserTemplateHandler(repo)
		auth.GET("/my-template", uth.List)

		oh := handlers.NewOrderHandler(repo, producer)
		auth.GET("/order", oh.List)
		auth.POST("/order", oh.Create)
		auth.GET("/order/:id", oh.Get)

		sh := handlers.NewSubmissionHandler(repo)
		auth.GET("/submission", sh.List)
		auth.POST("/submission", sh.Create)
		auth.GET("/submission/:id", sh.Get)
		auth.PATCH("/submission/:id", sh.Update)
		auth.DELETE("/submission/:id", sh.Delete)

		wh := handlers.NewWithdrawalHandler(repo)
		auth.GET("/withdrawal", wh.List)
		auth.POST("/withdrawal", wh.Create)
		auth.GET("/withdrawal/:id", wh.Get)
		auth.DELETE("/withdrawal/:id", wh.Delete)
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
		log.Printf("[template] HTTP server listening on :%s", cfg.HTTPPort)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[template] server error: %v", err)
		}
	}()

	<-quit
	log.Println("[template] shutting down...")
	consumeCancel()

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("[template] server forced to shutdown: %v", err)
	}
	log.Println("[template] exited")
}
