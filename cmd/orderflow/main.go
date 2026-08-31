package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/jiangyums/binance-orderflow-lab/internal/config"
	"github.com/jiangyums/binance-orderflow-lab/internal/engine"
)

func main() {
	configPath := flag.String("config", "configs/default.yaml", "config file path")
	flag.Parse()

	cfg, err := config.Load(*configPath)
	if err != nil {
		log.Fatalf("failed to load config: %v", err)
	}

	eng := engine.New(cfg)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	log.Printf("starting orderflow engine: symbol=%s", cfg.Symbol)
	if err := eng.Run(ctx); err != nil && err != context.Canceled {
		log.Fatalf("engine error: %v", err)
	}

	eng.Close()
	log.Println("orderflow engine stopped")
}
