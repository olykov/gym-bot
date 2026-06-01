FROM python:3.11-slim
WORKDIR /app

# Install the shared gym-api-client from the monorepo packages directory.
# The build context must be the repository root (docker build -f apps/bot/Dockerfile .).
COPY packages/api-contract/clients/python /tmp/gym-api-client
RUN pip install --no-cache-dir /tmp/gym-api-client

# Install remaining bot requirements.
COPY apps/bot/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot source.
COPY apps/bot/ .

CMD ["python", "main_webhook.py"]
