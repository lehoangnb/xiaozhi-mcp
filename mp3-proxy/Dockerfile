FROM node:18-alpine

RUN apk add --no-cache git ffmpeg wget ca-certificates

WORKDIR /app

# Clone api
RUN git clone https://github.com/lehoangnb/mp3-api

COPY mp3-proxy/package*.json ./

RUN npm install

COPY mp3-proxy/* .

# Install mp3-api dependencies
RUN cd mp3-api && npm install

EXPOSE 5005 5555

CMD ["sh", "-c", "cd mp3-api && npm start & node mp3-proxy.js"]
