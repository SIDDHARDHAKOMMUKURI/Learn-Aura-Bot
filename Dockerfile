FROM python:3.11-slim

# Install dependencies
RUN apt-get update && \
    apt-get install -y libreoffice curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Install Python deps
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "learnaurabot.py"]
