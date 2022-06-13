// Package utils holds some useful utitilies
package utils

import (
	"fmt"

	"github.com/sirupsen/logrus"
)

// Check runs a function and logs errors
// useful for error checking deferred functions
// i.g: defer Check(db.close)
func Check(f func() error) {
	if err := f(); err != nil {
		logrus.Error("Received error:", err)
	}
}

// PrintProgress prints out progress in percent
func PrintProgress(prefix string, current, total int) {
	fmt.Printf("\r [%s] Progress: %d/%d (%.1f%s)", prefix, current, total, float32(current)/float32(total)*100, "%")
}
