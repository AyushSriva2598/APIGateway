# High-Performance Rate Limiting Microservice

[![Node.js Version](https://img.shields.io/badge/node-%3E%3D%2018.0.0-blue.svg)](https://nodejs.org)
[![Database](https://img.shields.io/badge/database-PostgreSQL-blue.svg)](https://www.postgresql.org)
[![ORM](https://img.shields.io/badge/ORM-Prisma-purple.svg)](https://www.prisma.io)
[![Testing](https://img.shields.io/badge/testing-Jest%20%7C%20k6-red.svg)](https://jestjs.io)
[![Docker](https://img.shields.io/badge/docker-compatible-blue.svg)](https://www.docker.com)

A production-grade, standalone rate-limiting microservice designed to centralize and enforce API request limits across distributed systems. Rather than embedding complex rate-limiting logic within individual services, downstream APIs can query this service to dynamically authorize incoming requests.

---

## ⚡ Core Capabilities

- **Dual Algorithmic Engines**: Native support for both **Token Bucket** (for handling bursty traffic) and **Sliding Window Log** (for strict rate compliance) algorithms.
- **Concurrency & Atomicity**: Prevents token "double-spending" under highly concurrent request patterns by leveraging transaction-level pessimistic locking (`SELECT ... FOR UPDATE`) in PostgreSQL.
- **Dynamic Configuration**: Configure and update rate limits, burst sizes, and algorithms on a per-client basis at runtime without service restarts.
- **RFC-Compliant Headers**: Automatically appends standard rate limit metadata headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, and `X-RateLimit-Reset`) to response cycles.
- **Load Tested**: Benchmark validated using `k6` to successfully process **2,100+ requests/second** under load with 100% success rate (0 failures over 108,000+ total requests) in Redis-backed mode.

---

## 🏗️ System Architecture

![System Architecture](./assets/architecture_diagram.png)

---

## 🛠️ Technology Stack

- **Runtime**: Node.js (ES Modules, Express)
- **Database**: PostgreSQL (State store for buckets and sliding window log data)
- **ORM**: Prisma (Schema migrations & database queries)
- **Testing**: Jest (Unit testing) & Supertest (Integration testing)
- **Performance Benchmarking**: k6 (Load testing)
- **Deployment**: Docker & Docker Compose

---

## 🔌 API Reference

### 1. Client Administration

#### Create Client Profile
Create a client configuration profile specifying the rate-limiting algorithm and capacity parameters.

- **HTTP Method**: `POST`
- **Path**: `/admin/client`
- **Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "clientKey": "enterprise_user_99",
    "algorithm": "token_bucket",
    "rate": 10,
    "burst": 20
  }
  ```
  *(Supported algorithms: `"token_bucket"`, `"sliding_window"`)*
- **Response (`201 Created`)**:
  ```json
  {
    "message": "Client created successfully",
    "client": {
      "clientKey": "enterprise_user_99",
      "algorithm": "token_bucket",
      "rate": 10,
      "burst": 20
    }
  }
  ```

---

#### Get Client Profile
Retrieve the rate-limiting configuration of a specific client key.

- **HTTP Method**: `GET`
- **Path**: `/admin/client/:clientKey`
- **Response (`200 OK`)**:
  ```json
  {
    "clientKey": "enterprise_user_99",
    "algorithm": "token_bucket",
    "rate": 10,
    "burst": 20
  }
  ```

---

#### Update Client Profile
Modify the rate limits or burst threshold for an existing client profile.

- **HTTP Method**: `PUT`
- **Path**: `/admin/client/:clientKey`
- **Request Body**:
  ```json
  {
    "rate": 30,
    "burst": 50
  }
  ```
- **Response (`200 OK`)**:
  ```json
  {
    "message": "Client updated",
    "client": {
      "clientKey": "enterprise_user_99",
      "algorithm": "token_bucket",
      "rate": 30,
      "burst": 50
    }
  }
  ```

---

### 2. Request Authorization

#### Check Request Allowed
Inspects and registers a request attempt for a client key, evaluating limits against the configured algorithm.

- **HTTP Method**: `POST`
- **Path**: `/check`
- **Request Body**:
  ```json
  {
    "clientKey": "enterprise_user_99"
  }
  ```
- **Headers Returned**:
  - `X-RateLimit-Limit`: Maximum requests permitted in the window.
  - `X-RateLimit-Remaining`: Remaining capacity count for the current window.
  - `X-RateLimit-Reset`: Unix timestamp when the capacity fully refills.
- **Success Response (`200 OK` - Request Allowed)**:
  ```json
  {
    "allowed": true,
    "remaining": 19
  }
  ```
- **Limit Exceeded Response (`429 Too Many Requests` - Request Blocked)**:
  ```json
  {
    "allowed": false,
    "remaining": 0
  }
  ```

---

## 🔒 Concurrency Handling & Database Schema

To prevent race conditions during highly concurrent requests (e.g. if the same client fires 10 requests at the exact same millisecond), the repository utilizes **pessimistic row locking** via the PostgreSQL database engine. 

When a `/check` is processed:
1. A transaction begins.
2. The current bucket state is queried using `FOR UPDATE`:
   ```sql
   SELECT * FROM bucket_state WHERE client_key = $1 FOR UPDATE;
   ```
3. PostgreSQL locks the specific row, blocking concurrent evaluations on the same client key until the current transaction commits.
4. The remaining tokens are calculated, updated, and persisted, safely releasing the row lock.

### Database Tables

#### Client Config (`clients`)
Stores client profiles and configuration.
```sql
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_key TEXT UNIQUE NOT NULL,
    algorithm TEXT NOT NULL,
    rate INTEGER NOT NULL,
    burst INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Token Bucket State (`bucket_state`)
Maintains dynamic token balances and refill intervals.
```sql
CREATE TABLE bucket_state (
    client_key TEXT PRIMARY KEY REFERENCES clients(client_key) ON DELETE CASCADE,
    tokens DOUBLE PRECISION NOT NULL,
    last_refill TIMESTAMP NOT NULL
);
```

#### Sliding Window Request Log (`request_logs`)
Stores historical timestamp logs for rolling window evaluation.
```sql
CREATE TABLE request_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_key TEXT NOT NULL REFERENCES clients(client_key) ON DELETE CASCADE,
    request_time TIMESTAMP NOT NULL
);
```

---

### Redis-Backed Engine & Atomic Lua Scripts

When `LIMITER_STORAGE=redis` is enabled, the service shifts the rate-limiting evaluation and state storage entirely to Redis. Because Redis runs operations in a single thread, we achieve thread-safety and avoid race conditions without database transaction locking by evaluating **atomic Lua scripts** directly on the Redis server.

#### 1. Token Bucket in Redis
- **Data Structure**: Redis Hash (`rate_limiter:<clientKey>`) with fields `tokens` (float) and `last_refill` (timestamp).
- **Concurrency & TTL**: The Lua script loads the state, calculates refilled tokens based on the time elapsed since `last_refill`, consumes a token if allowed, and updates the hash. It dynamically calculates the key's TTL based on when the bucket will fully refill, allowing idle keys to clean themselves up automatically.

#### 2. Sliding Window Log in Redis
- **Data Structure**: Redis Sorted Set (ZSET) (`rate_limiter:sliding_window:<clientKey>`) where both the member and the score represent request timestamps in milliseconds.
- **Concurrency & TTL**: The Lua script performs the following atomic operations:
  1. Calls `ZREMRANGEBYSCORE` to prune all timestamps older than the sliding window boundary.
  2. Calls `ZCARD` to count the remaining requests.
  3. If allowed, calls `ZADD` to record the new request log.
  4. Sets the key expiration TTL to automatically purge the ZSET from memory once the window expires.

### 📊 Observability Stack (Prometheus & Grafana)

The microservice includes a fully pre-configured, production-ready observability pipeline to trace rate limit checks, monitor latency, and profile application replicas.

#### Exposed Custom Metrics
Our API instances collect and expose system and custom metrics at the `/metrics` endpoint. The custom metrics are:
- **`rate_limit_checks_total`** (Counter): Total rate-limiting checks processed. Labeled by:
  - `algorithm`: `token_bucket` or `sliding_window`
  - `storage`: `redis` or `postgres`
  - `result`: `allowed` or `blocked`
- **`rate_limit_check_duration_seconds`** (Histogram): High-resolution evaluation latency for rate check operations (configured with sub-millisecond buckets to capture fast Redis Lua script execution times).

#### Scrape & Dashboard Pipeline
1. **Instrumentation**: The application utilizes `prom-client` in Node.js to record latencies and outcome counters.
2. **Scraping**: Prometheus (port `9090`) uses Docker DNS A-record discovery (`dns_sd_configs`) to automatically identify all 3 running replicas of the `app` container and scrape them individually.
3. **Visualization**: Grafana (port `3000`) is pre-configured via yaml provisioning to load the Prometheus datasource automatically upon boot, enabling immediate dashboard creation.

---

## 🚀 Getting Started

### Prerequisites
- Node.js (v18.0.0+)
- PostgreSQL instance (local or containerized)

### Installation
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd TB_Rate_limiter
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Set up your environment variables:
   ```bash
   cp .env.example .env
   ```
   Modify `.env` to point to your PostgreSQL database instance:
   ```env
   DATABASE_URL="postgresql://user:password@localhost:5432/rate_limiter?schema=public"
   PORT=5000
   ```
4. Run database migrations:
   ```bash
   npx prisma migrate dev --name init
   ```

### Running the Server
- **Development Mode** (with hot-reloading):
  ```bash
   npm run dev
  ```
- **Production Mode**:
  ```bash
   npm run start
  ```

---

## 🧪 Testing

The test suite validates both unit correctness and behavior under load.

### 1. Run Unit & Integration Tests
Executes structural and route tests using Jest and Supertest:
```bash
npm run test
```

### 2. Run Load Tests
Performs concurrent capacity benchmarking using `k6`. Make sure the server is running, then execute:

**Option A: Run via Docker (Zero local installation)**
- **Standard Baseline Test**:
  ```bash
  docker run --rm --network host -i grafana/k6 run - <tests/load-test.js
  ```
- **High-Stress Spike Test** (50 concurrent clients, 300 VUs spike):
  ```bash
  docker run --rm --network host -i grafana/k6 run - <tests/load-test-crazy.js
  ```
- **Crash / Breaking Point Test** (1,500 VUs, no sleep):
  ```bash
  docker run --rm --network host -i grafana/k6 run - <tests/load-test-crash.js
  ```

**Option B: Run Locally**
- **Standard Baseline Test**:
  ```bash
  k6 run tests/load-test.js
  ```
- **High-Stress Spike Test**:
  ```bash
  k6 run tests/load-test-crazy.js
  ```
- **Crash / Breaking Point Test**:
  ```bash
  k6 run tests/load-test-crash.js
  ```

---

## 🐳 Docker Setup

A Docker Compose configuration is provided to spin up the application replicas, databases, and observability stack instantly.

1. **Build and run the entire cluster**:
   ```bash
   docker compose up --build
   ```
2. **Access Endpoints**:
   - **Rate Limiter API**: `http://localhost:5000` (Load-balanced via Nginx across 3 app replicas)
   - **Prometheus Dashboard**: `http://localhost:9090` (Checks active scrape targets and system metrics)
   - **Grafana Visualization**: `http://localhost:3000` (User: `admin` / Password: `admin`)
3. **Stop the environment**:
   ```bash
   docker compose down
   ```

---

## License

This project is licensed under the MIT License.
