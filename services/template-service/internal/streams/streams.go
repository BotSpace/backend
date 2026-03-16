package streams

import (
	"context"
	"encoding/json"
	"log"
	"strconv"

	"github.com/botspace/template-service/internal/config"
	"github.com/botspace/template-service/internal/repository"
	"github.com/redis/go-redis/v9"
)

// Producer publishes template events to Redis Streams.
type Producer struct {
	client *redis.Client
}

// NewProducer creates a new stream producer.
func NewProducer(client *redis.Client) *Producer {
	return &Producer{client: client}
}

// PublishOrderCreated publishes an order_created event.
func (p *Producer) PublishOrderCreated(ctx context.Context, orderID, userID, templateID uint, amount float64) error {
	return p.publish(ctx, config.StreamTemplateEvents, config.EventOrderCreated, map[string]interface{}{
		"order_id":    orderID,
		"user_id":     userID,
		"template_id": templateID,
		"amount":      amount,
	})
}

// PublishOrderConfirmed publishes an order_confirmed event.
func (p *Producer) PublishOrderConfirmed(ctx context.Context, orderID, userID, templateID uint) error {
	return p.publish(ctx, config.StreamTemplateEvents, config.EventOrderConfirmed, map[string]interface{}{
		"order_id":    orderID,
		"user_id":     userID,
		"template_id": templateID,
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

// Consumer reads payment events from Redis Streams.
type Consumer struct {
	client       *redis.Client
	repo         *repository.TemplateRepository
	producer     *Producer
	groupName    string
	consumerName string
}

// NewConsumer creates a new stream consumer.
func NewConsumer(client *redis.Client, repo *repository.TemplateRepository, producer *Producer, groupName, consumerName string) *Consumer {
	return &Consumer{
		client:       client,
		repo:         repo,
		producer:     producer,
		groupName:    groupName,
		consumerName: consumerName,
	}
}

// EnsureGroups creates consumer groups for streams the template service reads from.
func (c *Consumer) EnsureGroups(ctx context.Context) {
	streams := []string{config.StreamPaymentEvents}
	for _, s := range streams {
		err := c.client.XGroupCreateMkStream(ctx, s, c.groupName, "0").Err()
		if err != nil && err.Error() != "BUSYGROUP Consumer Group name already exists" {
			log.Printf("[streams] warning: could not create group for %s: %v", s, err)
		}
	}
}

// StartConsuming runs a blocking loop that reads and handles stream events.
func (c *Consumer) StartConsuming(ctx context.Context) {
	log.Println("[streams] template consumer started")
	for {
		select {
		case <-ctx.Done():
			log.Println("[streams] template consumer stopped")
			return
		default:
		}

		results, err := c.client.XReadGroup(ctx, &redis.XReadGroupArgs{
			Group:    c.groupName,
			Consumer: c.consumerName,
			Streams:  []string{config.StreamPaymentEvents, ">"},
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
	case config.EventPaymentSuccess:
		log.Printf("[streams] template received payment_success: %v", payload)
		c.handlePaymentSuccess(ctx, payload)
	default:
		log.Printf("[streams] template ignoring event: %s", eventType)
	}

	_ = c.client.XAck(ctx, stream, c.groupName, msg.ID)
}

// handlePaymentSuccess confirms a template order when payment succeeds.
func (c *Consumer) handlePaymentSuccess(ctx context.Context, payload map[string]interface{}) {
	orderIDRaw, ok := payload["order_id"]
	if !ok {
		log.Println("[streams] payment_success missing order_id")
		return
	}

	var orderID uint
	switch v := orderIDRaw.(type) {
	case float64:
		orderID = uint(v)
	case string:
		n, err := strconv.ParseUint(v, 10, 64)
		if err != nil {
			log.Printf("[streams] invalid order_id: %v", v)
			return
		}
		orderID = uint(n)
	}

	if err := c.repo.ConfirmOrder(orderID); err != nil {
		log.Printf("[streams] failed to confirm order %d: %v", orderID, err)
		return
	}
	log.Printf("[streams] order %d confirmed via payment_success", orderID)

	// Publish order_confirmed back to the stream
	userIDRaw, userOK := payload["user_id"]
	templateIDRaw, templateOK := payload["template_id"]
	if userOK && templateOK {
		userIDFloat, uok := userIDRaw.(float64)
		templateIDFloat, tok := templateIDRaw.(float64)
		if uok && tok {
			_ = c.producer.PublishOrderConfirmed(ctx, orderID, uint(userIDFloat), uint(templateIDFloat))
		} else {
			log.Printf("[streams] payment_success: unexpected type for user_id or template_id")
		}
	}
}
