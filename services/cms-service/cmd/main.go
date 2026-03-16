package main

import (
	"context"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/botspace/cms-service/internal/config"
	"github.com/botspace/cms-service/internal/handlers"
	"github.com/botspace/cms-service/internal/repository"
	"github.com/botspace/cms-service/internal/streams"
	"github.com/gin-gonic/gin"
	"github.com/redis/go-redis/v9"
	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

func main() {
	cfg := config.Load()

	// ---- MongoDB ----
	mongoCtx, mongoCancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer mongoCancel()

	mongoClient, err := mongo.Connect(mongoCtx, options.Client().ApplyURI(cfg.MongoURI))
	if err != nil {
		log.Fatalf("[cms] failed to connect to MongoDB: %v", err)
	}
	if err := mongoClient.Ping(mongoCtx, nil); err != nil {
		log.Fatalf("[cms] MongoDB ping failed: %v", err)
	}
	log.Println("[cms] connected to MongoDB")
	defer func() { _ = mongoClient.Disconnect(context.Background()) }()

	db := mongoClient.Database(cfg.MongoDB)
	repo := repository.New(db)

	// ---- Redis ----
	redisOpts, err := redis.ParseURL(cfg.RedisURL)
	if err != nil {
		log.Fatalf("[cms] invalid REDIS_URL: %v", err)
	}
	redisClient := redis.NewClient(redisOpts)
	if err := redisClient.Ping(context.Background()).Err(); err != nil {
		log.Fatalf("[cms] Redis ping failed: %v", err)
	}
	log.Println("[cms] connected to Redis")
	defer redisClient.Close()

	producer := streams.NewProducer(redisClient)
	consumer := streams.NewConsumer(redisClient, cfg.StreamGroup, "cms-consumer-1")

	// Ensure consumer groups exist
	consumer.EnsureGroups(context.Background())

	// Start consuming in the background
	consumeCtx, consumeCancel := context.WithCancel(context.Background())
	defer consumeCancel()
	go consumer.StartConsuming(consumeCtx)

	// ---- HTTP server ----
	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(gin.Logger())

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"status": "ok", "service": "cms"})
	})

	// Authenticated routes
	auth := router.Group("/api/v1", handlers.AuthMiddleware(cfg))
	{
		collectionHandler := handlers.NewCollectionHandler(repo, producer)

		col := auth.Group("/collection")
		{
			col.GET("", collectionHandler.List)
			col.POST("", collectionHandler.Create)
			col.GET("/:id", collectionHandler.Get)
			col.PATCH("/:id", collectionHandler.Update)
			col.DELETE("/:id", collectionHandler.Delete)
			col.GET("/:id/fields", collectionHandler.ListFields)
			col.POST("/:id/fields", collectionHandler.CreateField)
			col.POST("/:id/query", collectionHandler.Query)
			col.POST("/:id/export-excel", collectionHandler.ExportExcel)
			col.GET("/export-status/:task_id", collectionHandler.ExportStatus)
		}
	}

	srv := &http.Server{
		Addr:         ":" + cfg.HTTPPort,
		Handler:      router,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)

	go func() {
		log.Printf("[cms] HTTP server listening on :%s", cfg.HTTPPort)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("[cms] server error: %v", err)
		}
	}()

	<-quit
	log.Println("[cms] shutting down...")
	consumeCancel()

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()
	if err := srv.Shutdown(shutdownCtx); err != nil {
		log.Printf("[cms] server forced to shutdown: %v", err)
	}
	log.Println("[cms] exited")
}
