package config

import (
	"os"

	"gopkg.in/yaml.v3"
)

type Config struct {
	Symbol    string       `yaml:"symbol"`
	WebSocket WebSocketCfg `yaml:"websocket"`
	REST      RESTCfg      `yaml:"rest"`
	Signal    SignalCfg    `yaml:"signal"`
	Output    OutputCfg    `yaml:"output"`
	Latency   LatencyCfg   `yaml:"latency"`
	Monitor   MonitorCfg   `yaml:"monitor"`
}

type WebSocketCfg struct {
	DepthURL string `yaml:"depth_url"`
	TradeURL string `yaml:"trade_url"`
	Timeout  int    `yaml:"timeout_seconds"`
}

type RESTCfg struct {
	SnapshotURL string `yaml:"snapshot_url"`
	TimeURL     string `yaml:"time_url"`
	DepthLimit  int    `yaml:"depth_limit"`
}

type SignalCfg struct {
	TOFIThreshold float64 `yaml:"tofi_threshold"`
	TOFIScale     float64 `yaml:"tofi_scale"`
	TOFIMode      string  `yaml:"tofi_mode"`
}

type OutputCfg struct {
	Features   string `yaml:"features"`
	Signals    string `yaml:"signals"`
	Evaluation string `yaml:"evaluation"`
	Format     string `yaml:"format"`
}

type LatencyCfg struct {
	MaxMS     int64 `yaml:"max_ms"`
	GapWarnMS int64 `yaml:"gap_warn_ms"`
}

type MonitorCfg struct {
	IntervalSeconds int `yaml:"interval_seconds"`
}

func Load(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}

	cfg := &Config{}
	if err := yaml.Unmarshal(data, cfg); err != nil {
		return nil, err
	}

	// Set defaults
	if cfg.Symbol == "" {
		cfg.Symbol = "btcusdt"
	}
	if cfg.WebSocket.Timeout == 0 {
		cfg.WebSocket.Timeout = 30
	}
	if cfg.REST.DepthLimit == 0 {
		cfg.REST.DepthLimit = 1000
	}
	if cfg.Signal.TOFIScale == 0 {
		cfg.Signal.TOFIScale = 1.0
	}
	if cfg.Signal.TOFIMode == "" {
		cfg.Signal.TOFIMode = "linear"
	}
	if cfg.Output.Format == "" {
		cfg.Output.Format = "csv"
	}
	if cfg.Latency.MaxMS == 0 {
		cfg.Latency.MaxMS = 1000
	}
	if cfg.Latency.GapWarnMS == 0 {
		cfg.Latency.GapWarnMS = 3000
	}
	if cfg.Monitor.IntervalSeconds == 0 {
		cfg.Monitor.IntervalSeconds = 60
	}

	return cfg, nil
}
