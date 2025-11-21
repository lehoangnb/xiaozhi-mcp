FROM node:18-alpine

RUN apk add --no-cache ffmpeg wget ca-certificates

WORKDIR /app

COPY package*.json ./

RUN npm install

COPY . .

EXPOSE 5005

CMD ["node", "mp3-proxy.js"]
