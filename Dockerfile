FROM python:3.11-slim

# Install system dependencies for Playwright and PDF generation
RUN apt-get update && apt-get install -y     wget     gnupg     libgbm-dev     libnss3     libasound2     libxss1     libgtk-3-0     libatk-bridge2.0-0     libgtk-3-0     && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium --with-deps

COPY . .

EXPOSE 8000

CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
