package streams

import (
	"context"
	"encoding/json"
	"log"

	"github.com/botspace/payment-service/internal/config"
	"github.com/botspace/payment-service/internal/repository"
	"github.com/redis/go-redis/v9"
)

// Producer publishes payment events to Redis Streams.
type Producer struct {
	client *redis.Client
}

// NewProducer creates a new stream producer.
func NewProducer(client *redis.Client) *Producer {
	return &Producer{client: client}
}

// PublishPaymentSuccess publishes a payment_success event containing
// the transaction ID, user ID, amount, and (optionally) the related order ID.
func (p *Producer) PublishPaymentSuccess(ctx context.Context, transactionID, userID uint, amount float64, orderID *uint) error {
	payload := map[string]interface{}{
		"transaction_id": transactionID,
		"user_id":        userID,
		"amount":         amount,
	}
	if orderID != nil {
		payload["order_id"] = *orderID
	}
	return p.publish(ctx, config.StreamPaymentEvents, config.EventPaymentSuccess, payload)
}

// PublishPaymentFailed publishes a payment_failed event.
func (p *Producer) PublishPaymentFailed(ctx context.Context, transactionID, userID uint, amount float64) error {
	return p.publish(ctx, config.StreamPaymentEvents, config.EventPaymentFailed, map[string]interface{}{
		"transaction_id": transactionID,
		"user_id":        userID,
		"amount":         amount,
	})
}

func (p *Producer) publish(ctx context.Context, stream, eventType string, payload map[string]interface{}) error {
	data, err := json.Marshal(payload)
	if err != nil {
		return err
	}
	return p.client.XAdd(ctx, &redis.XAddArgs{
		Stream: stream,
		Values: map[string]interface{}{
			"event": eventType,
			"data":  string(data),
		},
	}).Err()
}

// Consumer reads template order events from Redis Streams.
type Consumer struct {
	client       *redis.Client
	repo         *repository.PaymentRepository
	producer     *Producer
	groupName    string
	consumerName string
}

// NewConsumer creates a new stream consumer.
func NewConsumer(client *redis.Client, repo *repository.PaymentRepository, producer *Producer, groupName, consumerName string) *Consumer {
	return &Consumer{
		client:       client,
		repo:         repo,
		producer:     producer,
		groupName:    groupName,
		consumerName: consumerName,
	}
}

// EnsureGroups creates consumer groups for streams the payment service reads.
func (c *Consumer) EnsureGroups(ctx context.Context) {
	streamNames := []string{config.StreamTemplateEvents}
	for _, s := range streamNames {
		err := c.client.XGroupCreateMkStream(ctx, s, c.groupName, "0").Err()
		if err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
			log.Printf("[streams] warning: could not create group for %s: %v", s, err)
		}
	}
}

// StartConsuming runs a blocking loop reading events from the template stream.
func (c *Consumer) StartConsuming(ctx context.Context) {
	log.Println("[streams] payment consumer started")
	for {
		select {
		case <-ctx.Done():
			log.Println("[streams] payment consumer stopped")
			return
		default:
		}

		results, err := c.client.XReadGroup(ctx, &redis.XReadGroupArgs{
			Group:    c.groupName,
			Consumer: c.consumerName,
			Streams:  []string{config.StreamTemplateEvents, ">"},
			Count:    10,
			Block:    0,
		}).Result()
		if err != nil {
			if err == context.Canceled {
				return
			}
			log.Printf("[streams] read error: %v", err)
			continue
		}

		for _, stream := range results {
			for _, msg := range stream.Messages {
				c.handleMessage(ctx, stream.Stream, msg)
			}
		}
	}
}

func (c *Consumer) handleMessage(ctx context.Context, stream string, msg redis.XMessage) {
	eventType, _ := msg.Values["event"].(string)
	dataStr, _ := msg.Values["data"].(string)

	var payload map[string]interface{}
	if err := json.Unmarshal([]byte(dataStr), &payload); err != nil {
		log.Printf("[streams] failed to parse message %s: %v", msg.ID, err)
		_ = c.client.XAck(ctx, stream, c.groupName, msg.ID)
		return
	}

	switch eventType {
	case config.EventOrderCreated:
		log.Printf("[streams] payment received order_created: %v", payload)
		// Payment service can react to new orders here (e.g., pre-validate balance)
	case config.EventOrderConfirmed:
		log.Printf("[streams] payment received order_confirmed: %v", payload)
	default:
		log.Printf("[streams] payment ignoring event: %s", eventType)
	}

	_ = c.client.XAck(ctx, stream, c.groupName, msg.ID)
}
