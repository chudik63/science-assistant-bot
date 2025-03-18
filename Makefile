postgres-up:
	docker-compose up postgres -d
	docker-compose up migrate
postgres-down:
	docker compose down
postgres-clear:
	docker volume rm science-assistant-bot_postgres_data
run:
	python3 main.py