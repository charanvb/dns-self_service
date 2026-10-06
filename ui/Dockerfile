FROM python:3.12-slim

WORKDIR /app

COPY ui/requirements.txt /app/ui/requirements.txt
RUN pip install --no-cache-dir -r /app/ui/requirements.txt

COPY shared /app/shared
COPY ui/app /app/ui/app

ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn ui.app.main:app --host 0.0.0.0 --port ${PORT}"]
