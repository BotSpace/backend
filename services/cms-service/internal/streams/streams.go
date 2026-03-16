package streams

import (
	"context"
	"encoding/json"
	"log"

	"github.com/botspace/cms-service/internal/config"
	"github.com/redis/go-redis/v9"
)

// Producer publishes events to Redis Streams.
type Producer struct {
	client *redis.Client
}

// NewProducer creates a new stream producer.
func NewProducer(client *redis.Client) *Producer {
	return &Producer{client: client}
}

// PublishCollectionCreated publishes a collection_created event.
func (p *Producer) PublishCollectionCreated(ctx context.Context, collectionID, projectID, name string) error {
	return p.publish(ctx, config.StreamCMSEvents, config.EventCollectionCreated, map[string]interface{}{
		"collection_id": collectionID,
		"project_id":    projectID,
		"name":          name,
	})
}

// PublishCollectionDeleted publishes a collection_deleted event.
func (p *Producer) PublishCollectionDeleted(ctx context.Context, collectionID, projectID string) error {
	return p.publish(ctx, config.StreamCMSEvents, config.EventCollectionDeleted, map[string]interface{}{
		"collection_id": collectionID,
		"project_id":    projectID,
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

// Consumer reads events from Redis Streams that are relevant to the CMS service.
type Consumer struct {
	client      *redis.Client
	groupName   string
	consumerName string
}

// NewConsumer creates a new stream consumer.
func NewConsumer(client *redis.Client, groupName, consumerName string) *Consumer {
	return &Consumer{
		client:       client,
		groupName:    groupName,
		consumerName: consumerName,
	}
}

// EnsureGroups creates consumer groups for streams the CMS service reads from.
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
// It should be started in a goroutine.
func (c *Consumer) StartConsuming(ctx context.Context) {
	log.Println("[streams] CMS consumer started")
	for {
		select {
		case <-ctx.Done():
			log.Println("[streams] CMS consumer stopped")
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
		log.Printf("[streams] CMS received payment_success event: %v", payload)
		// CMS can react to payment success here if needed (e.g., unlock content)
	default:
		log.Printf("[streams] CMS ignoring unknown event type: %s", eventType)
	}

	// Acknowledge the message
	_ = c.client.XAck(ctx, stream, c.groupName, msg.ID)
}
