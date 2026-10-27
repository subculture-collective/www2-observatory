FROM node:24-alpine AS frontend
WORKDIR /src/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM golang:1.27-alpine AS backend
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY cmd/ ./cmd/
COPY internal/ ./internal/
RUN CGO_ENABLED=0 go build -o /out/observatory ./cmd/observatory

FROM alpine:3.22
WORKDIR /app
RUN addgroup -S -g 10001 observatory && adduser -S -D -H -u 10001 -G observatory observatory
COPY --from=backend /out/observatory /app/observatory
COPY --from=frontend /src/frontend/dist /app/frontend/dist
ENV OBS_STATIC_DIR=/app/frontend/dist
USER observatory:observatory
ENTRYPOINT ["/app/observatory"]
CMD ["run"]
