package logging

import (
	"fmt"
	"log"
	"strings"
)

// LogLevel controls which messages a Logger writes.
type LogLevel uint8

const (
	ErrorLevel LogLevel = iota
	InfoLevel
	DebugLevel
)

// ParseLogLevel converts a log-level name into a LogLevel value.
func ParseLogLevel(value string) (LogLevel, error) {
	switch strings.ToLower(strings.TrimSpace(value)) {
	case "error":
		return ErrorLevel, nil
	case "info":
		return InfoLevel, nil
	case "debug":
		return DebugLevel, nil
	default:
		return ErrorLevel, fmt.Errorf("log_level must be one of: error, info, debug")
	}
}

// Logger filters formatted log messages according to a configured level.
type Logger struct {
	level  LogLevel
	logger *log.Logger
}

// NewLogger returns a Logger that writes to logger at the specified level.
func NewLogger(logger *log.Logger, level LogLevel) *Logger {
	return &Logger{level: level, logger: logger}
}

// Errorf logs an error-level formatted message.
func (logger *Logger) Errorf(format string, values ...any) {
	logger.log(ErrorLevel, "ERROR", format, values...)
}

// Infof logs an info-level formatted message.
func (logger *Logger) Infof(format string, values ...any) {
	logger.log(InfoLevel, "INFO", format, values...)
}

// Debugf logs a debug-level formatted message.
func (logger *Logger) Debugf(format string, values ...any) {
	logger.log(DebugLevel, "DEBUG", format, values...)
}

// log writes a message when the logger is configured to include the level.
func (logger *Logger) log(level LogLevel, name, format string, values ...any) {
	if logger == nil || logger.logger == nil || level > logger.level {
		return
	}
	logger.logger.Printf("%s %s", name, fmt.Sprintf(format, values...))
}
