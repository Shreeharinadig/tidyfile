export PYTHONPATH := worker:benchmark

.PHONY: help data eval eval-errors test test-python test-api up down clean

help:
	@echo "make data         generate the 50-file synthetic benchmark (seeded)"
	@echo "make eval         score the rule-based mapper; writes benchmark/results/latest.md"
	@echo "make eval-errors  same, and list mistakes on the dev split"
	@echo "make test         run Python tests"
	@echo "make test-api     run Java tests (needs Maven and Java 21)"
	@echo "make up / down    start or stop the local stack with the AWS emulator"

data:
	python3 benchmark/generate.py --out benchmark/data --seed 42

eval: data
	python3 benchmark/evaluate.py --mapper rules

eval-errors: data
	python3 benchmark/evaluate.py --mapper rules --show-errors

test: test-python

test-python:
	python3 -m pytest -q

test-api:
	mvn -B -f api/pom.xml test

up:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

down:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml down

clean:
	rm -rf benchmark/data .pytest_cache api/target
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
