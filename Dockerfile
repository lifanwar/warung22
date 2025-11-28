FROM node:22

WORKDIR /app

# Copy package dan lock file
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy seluruh source code
COPY . .

CMD ["npm", "run", "start"]