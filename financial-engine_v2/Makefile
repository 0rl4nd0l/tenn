up:
	test -f .env || (echo "Missing .env. Copy .env.example and set strong credentials before starting." && exit 1)
	docker compose up -d --build

migrate:
	docker compose exec backend alembic upgrade head

logs:
	docker compose logs -f --tail=200

down:
	docker compose down

impact-log:
	python3 scripts/log_change_impact.py $(ARGS)

context-refresh:
	python3 scripts/refresh_codex_context.py --mode workspace --write-config --config-path $$HOME/.codex/config.toml

context-check:
	python3 scripts/refresh_codex_context.py --mode workspace --check-significant

hooks-install:
	python3 scripts/install_git_hooks.py --set-hooks-path
