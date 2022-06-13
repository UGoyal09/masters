package main

import (
	"github.com/MaritimeOptima/services/pkg/errutils"
	internal "github.com/MaritimeOptima/voyage-predictions/tracks-builder2/internal"
	"github.com/MaritimeOptima/voyage-predictions/tracks-builder2/internal/config"
)

func main() {
	cfg, err := config.Init()
	errutils.Must(err)

	internal.Start(cfg)
}
