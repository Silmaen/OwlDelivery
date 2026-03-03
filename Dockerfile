FROM python:3.12-alpine

ENV PYTHONUNBUFFERED=1
EXPOSE 80
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    tzdata \
    nginx \
    nginx-mod-http-upload \
    nginx-mod-stream \
    nginx-mod-http-upload-progress \
    nginx-mod-http-encrypted-session

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY entrypoint.py /entrypoint.py
COPY server ./server

RUN chmod +x /entrypoint.py && \
    chmod -R 777 /app/server && \
    mkdir -p /app/staticfiles && chmod 777 /app/staticfiles

ENTRYPOINT ["/entrypoint.py"]
