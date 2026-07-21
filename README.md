# Wallet Ledger Service

A secure wallet and transaction management system built with Django, Django REST Framework, PostgreSQL, Redis, Celery, and Django Channels.

The system provides wallet management, deposit, withdrawal, transfer operations, transaction history, idempotent financial operations, concurrency-safe balance updates, and real-time wallet notifications.

---

## Tech Stack

- Python 3.12
- Django 5.2
- Django REST Framework
- PostgreSQL
- Redis
- Celery
- Django Channels
- WebSocket
- JWT Authentication (SimpleJWT)
- Docker & Docker Compose
- Pytest / Django Test Framework

---

# Features

## Authentication

- JWT based authentication using `djangorestframework-simplejwt`
- Access and refresh token support
- Protected REST APIs
- WebSocket authentication using JWT middleware

---

# Wallet Management

Users can:

- Create wallets
- View their wallets
- Check wallet balance
- Manage multiple currencies

Wallets support:

- Active / inactive status
- Currency isolation
- Balance tracking

---

# Transaction System

The transaction engine supports three transaction types:

## Deposit

Adds money to a wallet.

Flow:

1. Validate wallet existence
2. Check wallet status
3. Lock wallet row using database locking
4. Increase balance
5. Create ledger entry
6. Complete transaction


## Withdraw

Removes money from a wallet.

Flow:

1. Validate wallet
2. Check wallet status
3. Check sufficient balance
4. Lock wallet row
5. Decrease balance
6. Create ledger entry
7. Complete transaction


## Transfer

Transfers money between two wallets.

Flow:

1. Validate source and destination wallets
2. Prevent self-transfer
3. Lock wallets in deterministic order to avoid deadlocks
4. Validate currency compatibility
5. Check sufficient balance
6. Update both balances
7. Create debit and credit ledger entries
8. Complete transaction


---

# Transaction Safety

## Database Transactions

All financial operations use:

 transaction.atomic()


to guarantee consistency.

---

## Row Level Locking

Wallet balances are protected using:

select_for_update()


This prevents:

- Double spending
- Race conditions
- Incorrect balances during concurrent requests


---

## Idempotency

All transaction APIs support idempotency.

Each transaction has a unique:

```
idempotency_key
```

Sending the same request multiple times returns the original transaction instead of creating duplicate transactions.

Example:

```
POST /api/transactions/deposit/

{
    "wallet": 1,
    "amount": 100,
    "idempotency_key": "unique-key"
}
```

Repeated requests with the same key will not modify the wallet twice.

---

# Double Entry Ledger

Every transaction creates immutable ledger records.

Examples:

## Deposit

```
Wallet
 +100 CREDIT
```

## Withdraw

```
Wallet
 -100 DEBIT
```

## Transfer

```
Source Wallet
 -100 DEBIT

Destination Wallet
 +100 CREDIT
```

Ledger entries cannot be modified or deleted after creation.

This guarantees transaction history integrity.

---

# Large Transfer Monitoring

Large transfers are monitored automatically.

For transfers above the configured threshold:

- Celery task is triggered
- Monitoring notification is sent

Example:


notify_monitoring_team.delay(transaction_id)


---

# Real-time Notifications

Implemented using:

- Django Channels
- Redis Channel Layer
- WebSocket


Users receive wallet notifications instantly after receiving transfers.

WebSocket endpoint:

```
ws://host/ws/notifications/?token=<access_token>
```

Each authenticated user joins:

```
user_<user_id>
```

private channel group.

---

# API Endpoints

## Wallet APIs

```
GET    /api/wallets/
POST   /api/wallets/
GET    /api/wallets/{id}/
```

---

## Transaction APIs


### Deposit

```
POST /api/transactions/deposit/
```


Request:

```json
{
    "wallet": 1,
    "amount": "100",
    "idempotency_key": "uuid"
}
```


---

### Withdraw

```
POST /api/transactions/withdraw/
```


Request:

```json
{
    "wallet": 1,
    "amount": "50",
    "idempotency_key": "uuid"
}
```


---

### Transfer

```
POST /api/transactions/transfer/
```


Request:

```json
{
    "from_wallet": 1,
    "to_wallet": 2,
    "amount": "200",
    "idempotency_key": "uuid"
}
```


---

### Transaction History

```
GET /api/transactions/history/
```

Users can only see their own transactions.

---

# Testing

The project includes tests for:

## Service Layer

- Deposit success
- Deposit failure
- Withdraw success
- Insufficient balance
- Transfer success
- Transfer failure
- Idempotency behavior
- Ledger creation
- Notification triggering


## API Layer

- Authentication
- Validation errors
- Successful requests
- Idempotent requests
- Transaction history filtering


## Concurrency Tests

Concurrency scenarios are tested to verify:

- No double spending
- Correct final wallet balance
- Safe concurrent withdrawals/transfers


---

# Running With Docker

Build and start services:

```bash
docker compose up --build
```

Services:

- Django application
- PostgreSQL
- Redis
- Celery worker


---

# Running Tests

Inside Docker:

```bash
docker compose exec web python manage.py test
```

Run all tests:

```bash
docker compose exec web pytest
```


Run ASGI / Channels tests:

```bash
docker compose exec web pytest apps/notifications/tests
```


---

# Database Design

Main entities:

```
User
 |
Wallet
 |
Transaction
 |
TransactionLedger
```


## Transaction

Stores:

- transaction type
- amount
- status
- wallets involved
- creator
- timestamps


## TransactionLedger

Stores:

- transaction reference
- wallet
- debit/credit direction
- balance after transaction


Ledger records are immutable.

---

# Security Considerations

Implemented:

- JWT authentication
- Protected APIs
- Wallet ownership validation
- Idempotent financial operations
- Database row locking
- Immutable ledger
- Atomic transactions


---

# Project Structure

```
apps/
 ├── accounts/
 ├── wallets/
 ├── transactions/
 │    ├── api/
 │    ├── services/
 │    ├── models.py
 │    └── tasks.py
 └── notifications/

common/
 ├── middleware.py
 └── models.py

config/
 ├── settings/
 └── asgi.py
```

---

# Future Improvements

Possible extensions:

- Transaction export reports
- Audit logging
- Multi-currency exchange
- Admin monitoring dashboard
- Fraud detection system
- Kafka based event streaming