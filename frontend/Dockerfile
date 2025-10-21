# Use Node.js 20 LTS for better performance and stability
FROM node:20-alpine

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=development \
    NPM_CONFIG_LOGLEVEL=warn

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --legacy-peer-deps

# Copy application code
COPY . .

RUN chown -R node:node /app

USER node

# Expose Vite dev server port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5173 || exit 1

# Default command
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
