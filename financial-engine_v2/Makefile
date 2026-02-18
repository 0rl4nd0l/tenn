up:
	cp -n .env.example .env || true
	docker compose up -d --build

migrate:
	docker compose exec backend alembic upgrade head

logs:
	docker compose logs -f --tail=200

down:
	docker compose down
