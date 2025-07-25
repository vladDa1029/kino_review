.DEFAULT_GOAL := help

help:
	@echo list commands:
	@echo help  -  show list commands.
	@echo run -d   -  run docker-compose with flags -d.
	@echo build --pull  -  pull last version and build and up docker-compose file with flags -d.

up -d:
	docker-compose up -d


build --pull:
	git pull
	docker-compose up --build -d
