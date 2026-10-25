#!/bin/sh
# Railway startup — API only. Schema sync is handled in app lifespan via
# SQLAlchemy create_all, which creates MISSING tables only and never drops
# or truncates existing data.
#
# Alembic is intentionally NOT run here. Running "alembic upgrade head" against
# a live Railway DB that was bootstrapped via create_all can fail or conflict.
# To run migrations manually: railway run --service <backend> alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
