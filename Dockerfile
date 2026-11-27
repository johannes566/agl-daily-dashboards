FROM node:22-slim
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip tzdata && rm -rf /var/lib/apt/lists/* \
 && pip3 install --no-cache-dir --break-system-packages reportlab
ENV TZ=Africa/Johannesburg
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev || npm install --omit=dev
COPY . .
CMD ["node", "src/server.js"]
