FROM python:3.12-slim

WORKDIR /app

COPY functions/inventory_sync/requirements.txt /app/functions/inventory_sync/requirements.txt
RUN pip install --no-cache-dir -r /app/functions/inventory_sync/requirements.txt

COPY shared /app/shared
COPY functions/inventory_sync /app/functions/inventory_sync

ENTRYPOINT ["python", "-m", "functions.inventory_sync.sync"]
