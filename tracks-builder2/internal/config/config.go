// Package config is responsible of reading and exposing configs
package config

import (
	"github.com/MaritimeOptima/services/pkg/configs"
	dbutils "github.com/MaritimeOptima/services/pkg/helper/db"
	"github.com/sirupsen/logrus"
)

// Config holds the application configs
type Config struct {
	Environment string `env:"ENVIRONMENT"`

	DB             dbutils.Postgres `config_maps:"database"`
	configs.AzBlob `config_maps:"remote-storage"`

	Bucket string `env:"BUCKET" envDefault:"vesseltracks"`
}

// Init initializes the configs
func Init() (*Config, error) {
	cfg := Config{}

	err := configs.ParseConfigs(&cfg)
	if err != nil {
		return nil, err
	}

	return &cfg, nil
}

// OnChange is called when the config is changed
func (cfg Config) OnChange() {
	logrus.Info("Config changed")
}
