run:
	docker-compose up -d


build --pull:
	git pull
	docker-compose up --build -d
