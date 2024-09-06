
# Redis and aplication in one docker
- docker build -t fastapi-redis-app .
- docker run -p 8000:8000 -p 6379:6379 fastapi-redis-app