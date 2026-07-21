.PHONY: install deploy-inference dev-backend dev-frontend qdrant run stop build check

install:
	cp -n .env.example .env
	cd backend && go mod download
	cd frontend && npm install

deploy-inference:
	hf upload Eros483/autolinks-models ./inference/ --type space

dev-backend:
	cd backend && go run ./cmd/server

dev-frontend:
	cd frontend && npm run dev

qdrant:
	docker run -d --name autolinks-qdrant -p 6333:6333 -p 6334:6334 -v $$(pwd)/qdrant_storage:/qdrant/storage qdrant/qdrant

run: qdrant
	cd backend && go run ./cmd/server & \
	cd frontend && npm run dev & \
	wait

stop:
	@lsof -ti:8000 | xargs -r kill 2>/dev/null; \
	 lsof -ti:3000 | xargs -r kill 2>/dev/null; \
	 docker stop autolinks-qdrant 2>/dev/null; \
	 echo "stopped."

build:
	cd backend && go build -o server ./cmd/server

check:
	cd backend && go fmt ./... && git diff --exit-code
	cd backend && go vet ./... && golangci-lint run
	cd backend && go test -race ./...
	cd frontend && npm run lint && npm run test
