.PHONY: help upgrade downgrade migrate up up-infra down logs app register \
        gen-key test format lint lint-fix check

SRC := src
TESTS := tests

help:
	@echo ""
	@echo "  Миграции"
	@echo "    upgrade                   применить все миграции"
	@echo "    downgrade REV=<rev>       откатить до ревизии"
	@echo "    migrate MSG=<msg>         создать автомиграцию"
	@echo ""
	@echo "  Docker"
	@echo "    up                        postgres + приложение (миграции при старте)"
	@echo "    up-infra                  только postgres"
	@echo "    down                      остановить всё, volumes НЕ удаляются"
	@echo "    logs                      логи приложения"
	@echo ""
	@echo "  Локально"
	@echo "    app                       запустить приложение без Docker"
	@echo "    gen-key                   сгенерировать security.session_key"
	@echo "    register                  запасной вход в аккаунт из терминала (основной — через бота)"
	@echo ""
	@echo "  Качество кода"
	@echo "    check                     формат + линт + тесты"
	@echo "    test                      unit-тесты"
	@echo "    format | lint | lint-fix"
	@echo ""

# === Migrations ===

upgrade:
	uv run python -m alembic upgrade head

downgrade:
	uv run python -m alembic downgrade $(REV)

migrate:
	uv run python -m alembic revision --autogenerate -m "$(MSG)"

# === Docker ===

up:
	docker compose up --build -d

up-infra:
	docker compose up -d postgres

down:
	docker compose down

logs:
	docker compose logs -f app

# === Local ===

app:
	uv run python -m src.runtime.app

register:
	uv run python -m src.register_session

gen-key:
	@uv run python -c "from src.core.crypto import SessionCipher; print(SessionCipher.generate_key())"

# === Quality ===

test:
	uv run pytest $(TESTS)

format:
	uv run ruff format $(SRC) $(TESTS)

lint:
	uv run ruff check $(SRC) $(TESTS)

lint-fix:
	uv run ruff format $(SRC) $(TESTS)
	uv run ruff check --fix $(SRC) $(TESTS)

check: lint-fix test
