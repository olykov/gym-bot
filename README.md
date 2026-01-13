# Telegram Gym Bot

A production-ready Telegram bot for tracking gym workouts with PostgreSQL database storage, Redis FSM state management, and web-based admin panel.

## 📱 Screenshots

<p align="center">
  <img src="src/img01.PNG" width="30%" />
  <img src="src/img02.PNG" width="30%" />
  <img src="src/img03.PNG" width="30%" />
</p>

<p align="center">
  <img src="src/graph.png" width="60%" />
</p>

## 📋 Overview

This Telegram bot helps users track their gym workouts by guiding them through a step-by-step process to record exercises, sets, weights, and repetitions. The data is stored in a PostgreSQL database with Redis-backed FSM state management for reliable webhook-based operation.

## 🏛️ Architecture Highlights

### Production-Ready Infrastructure
- **Webhook-Based**: Fast, scalable webhook mode with signature validation
- **Redis FSM**: Persistent state management survives process restarts
- **Connection Pooling**: Thread-safe PostgreSQL connection management (2-10 connections)
- **Multi-Container**: Isolated services (bot, database, Redis, admin backend/frontend)
- **Secure**: HMAC webhook validation, JWT admin authentication

### Key Technical Features
- **Smart Exercise Prioritization**: ML-like frequency analysis shows user's top exercises first
- **Personal Record Tracking**: Automatic PR calculation across all training history
- **User Customization**: Global + private exercise/muscle management per user
- **Intelligent History**: Context-aware display of complete previous sessions
- **Fast Navigation**: One-tap "Continue Exercise" for workout flow

## 🏗️ Project Structure

```
tg_gym_bot/
├── app/                          # Main application directory
│   ├── main_webhook.py           # Production webhook entry point (ACTIVE)
│   ├── main.py                   # Development/hybrid mode
│   ├── Dockerfile                # Bot container configuration
│   ├── modules/                  # Core application modules
│   │   ├── handlers.py          # Telegram bot message/callback handlers
│   │   ├── states.py            # FSM state definitions
│   │   ├── logging.py           # Custom JSON logger implementation
│   │   └── postgres.py          # PostgreSQL with connection pooling
│   ├── templates/               # Data templates and configurations
│   │   └── exercise.py          # Exercise types, weights, reps definitions
│   └── utils/                   # Utility functions
│       └── markups.py           # Telegram inline keyboard markup generators
├── admin_panel/                 # Web-based admin interface
│   ├── backend/                 # FastAPI admin backend
│   │   ├── main.py              # Admin API entry point
│   │   ├── app/api/v1/          # API routes (muscles, exercises, training)
│   │   └── Dockerfile           # Backend container
│   └── frontend/                # Admin web UI
│       └── Dockerfile           # Frontend container
├── src/                         # Static assets
│   ├── img01.PNG                # Bot screenshot 1
│   ├── img02.PNG                # Bot screenshot 2
│   ├── img03.PNG                # Bot screenshot 3
│   └── graph.png                # Analytics graph
├── docker-compose.yaml          # Multi-container orchestration
├── init.sql                     # Database schema initialization
└── requirements.txt             # Python dependencies
```

## 🚀 Technologies Used

### Core Technologies
- **Python 3.10** - Main programming language
- **aiogram 3.18.0** - Telegram Bot API framework with FSM support
- **FastAPI 0.115.11** - Web framework for webhook handling and admin API
- **PostgreSQL 16** - Primary database with connection pooling
- **Redis 7** - FSM state storage and session management
- **Docker & Docker Compose** - Multi-container orchestration

### Key Dependencies
- **psycopg2-binary 2.9.10** - PostgreSQL adapter with ThreadedConnectionPool
- **redis-py** - Async Redis client for FSM storage
- **prettytable 3.15.1** - Formatted table output
- **python-json-logger 3.2.1** - Structured JSON logging
- **uvicorn 0.34.0** - ASGI server for webhook handling

### Infrastructure & Security
- **Redis FSM Storage** - Persistent state management across webhook requests
- **Webhook Signature Validation** - HMAC-based request authentication
- **Connection Pooling** - Thread-safe database connection management
- **JWT Authentication** - Secure admin panel access
- **Docker Compose** - 5-container production architecture

## 🔧 Features

### Core Functionality
- **Interactive Workout Tracking**: Step-by-step guided process for recording workouts
- **Exercise Categories**: Support for 8+ muscle groups (Chest, Biceps, Back, Triceps, Shoulders, Forearms, Legs, Abs)
- **Comprehensive Exercise Database**: 100+ predefined exercises with user extension capability
- **Set Tracking**: Track up to 6 sets per exercise
- **Weight & Reps Recording**: Detailed weight (1kg - 180kg) and rep (1-20) tracking
- **Duplicate Prevention**: Prevents recording the same set twice on the same day
- **Training History Display**: Shows user's last training session for each exercise with detailed set/weight/reps breakdown
- **Personal Record (PR) Tracking**: Displays user's maximum weight achieved for each exercise with reps and date
- **Smart Exercise Prioritization**: Shows user's top 5 most-used exercises first for each muscle group
- **Compact Exercise View**: Displays only top exercises initially with "Show All" option for full access
- **Continue Exercise**: Quick continuation of the same exercise with one-tap access to next set

### User Experience
- **Inline Keyboard Navigation**: Easy-to-use button-based interface
- **Back Navigation**: Users can navigate back through previous selections
- **Progress Tracking**: Visual feedback on completed sets
- **Formatted Results**: Clean table format for workout summaries
- **Historical Context**: Automatic display of last training performance when selecting exercises
- **Personal Record Motivation**: Instant display of personal bests with complete context (weight + reps) to encourage progression
- **Personalized Exercise Order**: Most-used exercises appear first for faster access
- **Streamlined Interface**: See only relevant exercises initially with optional full access
- **First-time User Friendly**: Clear messaging for users who haven't done specific exercises before
- **Smart History Logic**: Shows complete previous sessions, not partial current-day progress

### User Exercise Management
- **Add Custom Muscles**: Users can create their own muscle groups
- **Add Custom Exercises**: Add personalized exercises to any muscle group
- **Delete/Hide Exercises**: Remove or hide unwanted exercises from the interface
- **Private Exercise Library**: Each user has their own custom exercise collection
- **Global + Private Mix**: Access both predefined and custom exercises seamlessly

### Data Management
- **PostgreSQL Storage**: Reliable primary data storage with ACID compliance
- **Redis FSM State**: Persistent state management across webhook requests
- **Connection Pooling**: Thread-safe database connection management (2-10 connections)
- **User Registration**: Automatic user registration on first interaction
- **Data Integrity**: Hash-based unique identifiers for training records
- **Training History Retrieval**: Efficient queries to fetch user-specific exercise history
- **Personal Record Calculation**: Optimized queries to find maximum weights across all training sessions
- **Exercise Frequency Analysis**: Tracks and ranks exercises by usage frequency for personalization
- **Session Grouping**: Smart grouping of training data by date for historical context

### Admin Panel (Web Interface)
- **JWT Authentication**: Secure admin access with token-based auth
- **Muscle Management**: CRUD operations for global muscle groups
- **Exercise Management**: CRUD operations for global exercises
- **Training Records**: View and manage all training data
- **User Analytics**: Track user activity and training patterns
- **RESTful API**: FastAPI-based backend at port 8001
- **Modern Web UI**: React-based frontend at port 5174

## 🏃‍♂️ Deployment Architecture

The bot runs in **production webhook mode** with the following architecture:

### Production Mode (Active)
- **Entry Point**: `main_webhook.py`
- **Mode**: Webhook-based with FastAPI
- **State Storage**: Redis FSM (persistent across requests)
- **Security**: Webhook signature validation with `X-Telegram-Bot-Api-Secret-Token`
- **Connection Management**: Thread-safe connection pooling (2-10 connections)
- **Port**: 5400

### Multi-Container Setup
The production deployment consists of 5 Docker containers:
1. **gymbot_backend** - Main Telegram bot (main_webhook.py)
2. **gymbot_redis** - Redis 7 for FSM state storage
3. **gymbot_db** - PostgreSQL 16 database
4. **admin_backend** - FastAPI admin API (port 8001)
5. **admin_frontend** - Web admin UI (port 5174)

### Development Mode (Optional)
- **Entry Point**: `main.py`
- **Mode**: Hybrid (polling + webhook endpoint for testing)
- Use for local development without Redis dependency

## 💾 Database Schema

```sql
-- Users table
users (
    id BIGINT PRIMARY KEY,           -- Telegram user ID
    registration_date TIMESTAMP,     -- When user first used bot
    last_interaction TIMESTAMP,      -- Last activity
    lastname VARCHAR(255),           -- User's last name
    first_name VARCHAR(255),         -- User's first name
    username VARCHAR(255),           -- Telegram username
    bio TEXT                         -- User bio
)

-- Muscle groups (global + user-created)
muscles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE,        -- Muscle group name
    is_global BOOLEAN DEFAULT TRUE,  -- Global (visible to all) or private
    created_by BIGINT                -- User ID of creator (for private muscles)
)

-- Exercises (global + user-created)
exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),               -- Exercise name
    muscle INT REFERENCES muscles(id), -- Associated muscle group
    is_global BOOLEAN DEFAULT TRUE,  -- Global (visible to all) or private
    created_by BIGINT,               -- User ID of creator (for private exercises)
    UNIQUE(name, muscle)
)

-- User hidden muscles (allows users to hide global muscles)
user_hidden_muscles (
    user_id BIGINT REFERENCES users(id),
    muscle_id INT REFERENCES muscles(id),
    PRIMARY KEY (user_id, muscle_id)
)

-- User hidden exercises (allows users to hide global exercises)
user_hidden_exercises (
    user_id BIGINT REFERENCES users(id),
    exercise_id INT REFERENCES exercises(id),
    PRIMARY KEY (user_id, exercise_id)
)

-- Training records
training (
    id VARCHAR(32) PRIMARY KEY,      -- MD5 hash ID
    date TIMESTAMP,                  -- Workout timestamp
    user_id BIGINT REFERENCES users(id),
    muscle_id INT REFERENCES muscles(id),
    exercise_id INT REFERENCES exercises(id),
    set INT,                         -- Set number (1-6)
    weight DECIMAL(5,2),             -- Weight in kg
    reps DECIMAL(5,2)                -- Number of repetitions
)
-- Used for training history display, personal record calculation, and progress tracking
```

## 🛠️ Setup & Installation

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Telegram Bot Token (get from [@BotFather](https://t.me/botfather))
- Domain with SSL certificate (for webhook)

### Environment Variables
Create a `.env` file with the following variables:

```bash
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret_token
WEB_APP_URL=your.domain.com

# Database Configuration
DB_NAME=gymbot
DB_USER=postgres
DB_PASSWORD=your_db_password
DB_HOST=gymbot_db
DB_PORT=5432

# Redis Configuration
REDIS_HOST=gymbot_redis
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Docker Images (for deployment)
BOT_IMAGE=your_registry/gymbot
BOT_TAG=latest
ADMIN_BACKEND_IMAGE=your_registry/admin-backend
ADMIN_BACKEND_TAG=latest
ADMIN_FRONTEND_IMAGE=your_registry/admin-frontend
ADMIN_FRONTEND_TAG=latest
```

### Docker Deployment

#### Local Development
```bash
# Clone the repository
git clone <repository_url>
cd tg-app-gym-bot

# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Build images
docker-compose build

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f gymbot_backend
docker-compose logs -f admin_backend

# Verify webhook registration
curl https://api.telegram.org/bot<YOUR_TOKEN>/getWebhookInfo
```

#### Production Deployment
```bash
# Build and push Docker images
docker build -t your_registry/gymbot:latest ./app
docker push your_registry/gymbot:latest

docker build -t your_registry/admin-backend:latest ./admin_panel/backend
docker push your_registry/admin-backend:latest

docker build -t your_registry/admin-frontend:latest ./admin_panel/frontend
docker push your_registry/admin-frontend:latest

# On production server
docker-compose pull
docker-compose up -d

# Verify all services are running
docker-compose ps
```

### Accessing Services
- **Telegram Bot**: Available via webhook at `https://your.domain.com/webhook`
- **Admin API**: http://localhost:8001/docs (Swagger UI)
- **Admin Frontend**: http://localhost:5174
- **Database**: localhost:9981 (mapped from container port 5432)

## 🎯 Usage

1. **Start the bot**: Send `/start` to initiate
2. **Begin workout**: Click "Record training" or send `/gym`
3. **Select muscle group**: Choose from 8 available categories
4. **Pick exercise**: Select from muscle-specific exercises
   - **NEW**: Smart compact view shows only your top exercises (1-5 based on training history)
   - **NEW**: "Show All" button provides access to complete exercise list when needed
   - If no training history, shows all exercises (same as before)
   - **NEW**: Bot automatically shows your last training history for this exercise
   - Shows formatted table with previous sets, weights, and reps
   - **NEW**: Displays your Personal Record (PR) - maximum weight ever lifted for this exercise with reps
   - If first time doing exercise, shows friendly "You haven't done [exercise] before" message
5. **Choose set number**: Pick which set you're recording
6. **Enter weight**: Select weight used
7. **Enter reps**: Record number of repetitions
8. **Review**: Bot displays formatted summary and allows new entries

### Available Commands
- `/start` - Initialize bot and show main menu
- `/gym` - Start recording a new workout
- `/edit` - Access exercise management (add/delete custom muscles and exercises)

### 📊 Training History & Personal Records Feature

When you select an exercise, the bot automatically displays your most recent **previous** training session and personal record:

**For existing exercises:**
```
📊 Your last training for Bench press (15-12-2024):

+-------+-------------+------+
| Set   | Weight (kg) | Reps |
+-------+-------------+------+
| Set 1 | 60kg        | 10   |
| Set 2 | 65kg        | 8    |
| Set 3 | 65kg        | 6    |
+-------+-------------+------+

Your PR: 80kg for 5 reps (10 December 2024)

Select set
```

**For new exercises:**
```
📝 You haven't done Incline press before.

Select set
```

This feature helps you:
- **Track Progress**: See your previous performance instantly
- **Beat Personal Records**: Know your current PR to aim higher
- **Plan Sets**: Make informed decisions about weights and reps
- **Stay Motivated**: Visual progress tracking across sessions
- **Consistency**: Maintain workout intensity based on historical data
- **Clear Reference**: Shows only complete previous sessions, not today's incomplete progress

### 🎯 Smart Exercise Prioritization & Compact View

When you select a muscle group, the bot shows a streamlined interface based on your training patterns:

**For experienced users (Compact View):**
```
User's most frequent Chest exercises:
1. Bench press (15 sessions)
2. Dumbbell press flat bench (12 sessions)  
3. Incline smith (8 sessions)
4. Chest press machine (5 sessions)
5. Hammer flat (3 sessions)

Initial display (Compact View):
[Bench press] [Chest press machine] [Dumbbell press flat bench] [Hammer flat] [Incline smith]
[Show All] [⬅️ Go back]

After clicking "Show All":
[Bench press] [Chest press machine] [Dumbbell press flat bench] [Hammer flat] [Incline smith]
[Bench press incline] [Dumbbell incline bench press] [Lower chest cable crossover] ...
[⬅️ Go back]
```

**For users with some history (1-4 exercises):**
```
Shows only exercises you've done before:
[Bench press] [Incline smith]
[Show All] [⬅️ Go back]
```

**For new users:**
```
Shows all exercises (current behavior):
[Bench press] [Bench press incline] [Dumbbell incline bench press] ...
[⬅️ Go back]
```

This feature provides:
- **Faster Access**: See only your favorite exercises initially
- **Clean Interface**: No scrolling through irrelevant exercises
- **Full Access**: "Show All" always available when needed
- **Smart Adaptation**: Interface automatically adapts to your experience level
- **Progressive Learning**: Bot learns and improves recommendations over time

### 🧠 Smart Training History Logic

The bot intelligently handles training history display to provide the most useful reference information:

**Scenario: User completes Set 1 today, then selects same exercise again**
```
❌ OLD BEHAVIOR (confusing):
"📊 Your last training for Bench press (15-01-2025):
Set 1 | 60kg | 8 reps"  ← Shows today's incomplete session

✅ NEW BEHAVIOR (helpful):
"📊 Your last training for Bench press (10-01-2025):
Set 1 | 55kg | 10 reps
Set 2 | 60kg | 8 reps
Set 3 | 60kg | 6 reps"  ← Shows previous complete session for reference
```

**Benefits:**
- **🎯 Relevant Reference**: Always shows a complete previous workout session
- **📊 Better Planning**: Compare with full training data, not partial current session
- **🚫 No Confusion**: Eliminates seeing incomplete current progress as "last training"
- **🧠 Intelligent Logic**: Bot understands the difference between current and reference data

## 🔒 Security Features

### Bot Security
- **Input Validation**: All user inputs are validated against predefined options
- **SQL Injection Prevention**: Uses parameterized queries with psycopg2
- **Webhook Signature Validation**: Validates `X-Telegram-Bot-Api-Secret-Token` header
- **Environment Variable Protection**: Sensitive data stored in environment variables
- **Connection Pooling**: Thread-safe database access prevents race conditions

### Admin Panel Security
- **JWT Authentication**: Token-based authentication for admin access
- **CORS Configuration**: Configurable cross-origin access control
- **Session Management**: Secure session token verification
- **User Isolation**: Private exercises/muscles isolated per user

## 📊 Logging

The application uses structured JSON logging with the following levels:
- **INFO**: User actions, successful operations
- **ERROR**: Database errors, API failures
- **WARNING**: Validation issues, missing data

## 🚀 API Endpoints

### Bot Webhook API (Port 5400)
- `POST /webhook` - Telegram webhook endpoint (with signature validation)

### Admin API (Port 8001)
Authentication required: `Authorization: Bearer <JWT_TOKEN>`

**Muscle Management:**
- `GET /api/v1/muscles` - List all muscle groups
- `POST /api/v1/muscles` - Create new muscle group
- `PUT /api/v1/muscles/{muscle_id}` - Update muscle group
- `GET /api/v1/user/muscles` - Get user-visible muscles

**Exercise Management:**
- `GET /api/v1/exercises` - List all exercises
- `POST /api/v1/exercises` - Create new exercise
- `PUT /api/v1/exercises/{exercise_id}` - Update exercise
- `GET /api/v1/user/exercises?muscle_id={id}` - Get user-visible exercises for muscle

**Training Records:**
- `GET /api/v1/training` - List training records (paginated)
- `GET /api/v1/static-data` - Get sets/weights/reps options

**User Management:**
- `GET /api/v1/user/profile` - Get current user profile

**Documentation:**
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

## ⚡ Performance & Scalability

### Response Times
- **Webhook Processing**: < 100ms for most operations
- **Database Queries**: Optimized indexes on training(user_id, date, exercise_id)
- **Exercise Prioritization**: Cached frequency analysis
- **FSM State Access**: Redis in-memory operations < 1ms

### Scalability
- **Concurrent Users**: Supports 100+ concurrent users
- **Connection Pooling**: 2-10 PostgreSQL connections (adjustable)
- **Redis State Storage**: No memory leaks, automatic TTL (24h)
- **Webhook Mode**: Horizontal scaling ready (stateless with Redis)

### Resource Usage
- **Memory**: ~100MB per bot instance
- **CPU**: Low usage (<5% idle, <30% under load)
- **Database**: ~1KB per training record
- **Redis**: ~10KB per active user session

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🐛 Known Issues & Limitations

- **Webhook URL**: Requires HTTPS domain with valid SSL certificate
- **Redis Dependency**: Bot requires Redis for FSM state storage (cannot run without it in webhook mode)
- **Admin Panel Authentication**: Initial admin user must be created manually in database
- **Exercise Limit**: Inline keyboard limited to ~40 buttons per message (Telegram API limitation)

## 📞 Support

For issues and questions, please open an issue in the GitHub repository.
