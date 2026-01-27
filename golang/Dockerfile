# Build stage
FROM golang:1.25-alpine AS builder

WORKDIR /app

# Install git for fetching dependencies
RUN apk add --no-cache git

# Copy go mod files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the binary
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /crawler ./cmd/crawler

# Runtime stage
FROM alpine:3.23

# Install CA certificates for HTTPS
RUN apk add --no-cache ca-certificates

# Copy binary from builder
COPY --from=builder /crawler /usr/local/bin/crawler

# Run as non-root user
RUN adduser -D -u 1000 crawler
USER crawler

ENTRYPOINT ["crawler"]
