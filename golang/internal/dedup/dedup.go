package dedup

// Deduplicator provides URL deduplication functionality.
type Deduplicator interface {
	// SeenOrAdd checks if URL was seen and adds it if not.
	// Returns true if the URL was already seen.
	SeenOrAdd(url string) bool

	// Seen checks if URL was seen without adding it.
	Seen(url string) bool

	// Count returns the approximate number of items added.
	Count() uint64
}
