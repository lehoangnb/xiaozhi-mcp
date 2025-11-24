FROM node:18-alpine

RUN apk add --no-cache ffmpeg wget ca-certificates

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

# Install mp3-api dependencies
RUN cd mp3-api && npm install

EXPOSE 5005 5555

CMD ["sh", "-c", "cd mp3-api && npm start & node mp3-proxy.js"]
