.DEFAULT_GOAL := help

.PHONY:
help:
	@echo "Available commands:"
	@echo "  make help      - Show this help"
	@echo "  make run       - Run docker-compose in background (with -d)"
	@echo "  make run-dev   - Run docker-compose in foreground"
	@echo "  make build     - Pull, rebuild and start containers"


.PHONY:
run:
	docker-compose up -d

.PHONY:
run-dev:
	docker-compose up

.PHONY:
build:
	git pull
	docker-compose up --build -d