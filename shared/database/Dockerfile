FROM python:3.12-slim

WORKDIR /app

COPY shared/database/requirements.txt /app/shared/database/requirements.txt
RUN pip install --no-cache-dir -r /app/shared/database/requirements.txt

COPY shared /app/shared

WORKDIR /app/shared/database
ENTRYPOINT ["alembic", "upgrade", "head"]
