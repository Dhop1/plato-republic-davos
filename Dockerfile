# 1. Start with a lightweight Python base
FROM python:3.11-slim

# 2. Install system dependencies and Node.js (v20)
RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Install Node Dependencies First
COPY package*.json ./
RUN npm install

# 4. Install Python Dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code
COPY . .

# 6. Build the Vite/React frontend
RUN npm run build

# 7. Ensure execution rights
RUN chmod +x start.sh

# 8. Expose necessary ports
EXPOSE 5001 3000

# 9. Execute the dual-boot script
CMD ["bash", "start.sh"]
