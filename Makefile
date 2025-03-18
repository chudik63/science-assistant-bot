postgres:
	docker-compose up postgres -d
	docker-compose up migrate
run:
	python3 main.py