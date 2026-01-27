package frontier

import (
	"context"
	"time"

	"github.com/redis/go-redis/v9"
)

// RedisFrontier is a Redis-backed URL queue for distributed crawling.
type RedisFrontier struct {
	client *redis.Client
	key    string
}

// NewRedisFrontier creates a new Redis-backed frontier.
func NewRedisFrontier(addr, key string) (*RedisFrontier, error) {
	client := redis.NewClient(&redis.Options{
		Addr: addr,
	})

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := client.Ping(ctx).Err(); err != nil {
		return nil, err
	}

	return &RedisFrontier{
		client: client,
		key:    key,
	}, nil
}

// Push adds a URL to the queue using RPUSH.
func (f *RedisFrontier) Push(ctx context.Context, url string) error {
	return f.client.RPush(ctx, f.key, url).Err()
}

// Pop removes and returns a URL from the queue using BLPOP.
func (f *RedisFrontier) Pop(ctx context.Context) (string, error) {
	result, err := f.client.BLPop(ctx, 0, f.key).Result()
	if err != nil {
		return "", err
	}
	// BLPop returns [key, value]
	return result[1], nil
}

// PopWithTimeout removes and returns a URL with a timeout using BLPOP.
func (f *RedisFrontier) PopWithTimeout(ctx context.Context, timeout time.Duration) (string, error) {
	result, err := f.client.BLPop(ctx, timeout, f.key).Result()
	if err == redis.Nil {
		return "", nil // Timeout, not an error
	}
	if err != nil {
		return "", err
	}
	return result[1], nil
}

// Size returns the current number of URLs in the queue.
func (f *RedisFrontier) Size() int64 {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	size, err := f.client.LLen(ctx, f.key).Result()
	if err != nil {
		return 0
	}
	return size
}

// Close closes the Redis connection.
func (f *RedisFrontier) Close() error {
	return f.client.Close()
}
