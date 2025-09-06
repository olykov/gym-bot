# Telegram Gym Bot

A Telegram bot for tracking gym workouts with PostgreSQL database storage and Google Sheets backup integration.

## 📋 Overview

This Telegram bot helps users track their gym workouts by guiding them through a step-by-step process to record exercises, sets, weights, and repetitions. The data is stored in a PostgreSQL database with optional Google Sheets backup for admin users.

## 🏗️ Project Structure

```
tg_gym_bot/
├── app/                          # Main application directory
│   ├── main.py                   # Hybrid main (polling + webhook)
│   ├── main_longpolling.py       # Long polling mode entry point
│   ├── main_webhook.py           # Webhook mode entry point
│   ├── modules/                  # Core application modules
│   │   ├── __init__.py          # Module exports
│   │   ├── handlers.py          # Telegram bot message/callback handlers
│   │   ├── logging.py           # Custom JSON logger implementation
│   │   ├── postgres.py          # PostgreSQL database operations
│   │   └── sheets.py            # Google Sheets integration
│   ├── templates/               # Data templates and configurations
│   │   └── exercise.py          # Exercise types, weights, reps definitions
│   └── utils/                   # Utility functions
│       └── markups.py           # Telegram inline keyboard markup generators
├── ansible/                     # Deployment automation
│   ├── deploy.yaml              # Main deployment playbook
│   ├── files/                   # Deployment files
│   │   ├── docker-compose.yaml  # Docker Compose configuration
│   │   └── init.sql             # Database initialization script
│   ├── group_vars/              # Ansible variables
│   │   └── all.yaml             # Global variables
│   ├── inventory.yaml           # Ansible inventory configuration
│   └── requirements.yaml        # Ansible dependencies
├── Dockerfile                   # Docker container configuration
└── requirements.txt             # Python dependencies
```

## 🚀 Technologies Used

### Core Technologies
- **Python 3.10** - Main programming language
- **aiogram 3.18.0** - Telegram Bot API framework
- **FastAPI 0.115.11** - Web framework for webhook handling
- **PostgreSQL 16** - Primary database
- **Docker & Docker Compose** - Containerization

### Key Dependencies
- **psycopg2-binary 2.9.10** - PostgreSQL adapter
- **gspread 6.2.0** - Google Sheets integration
- **prettytable 3.15.1** - Formatted table output
- **python-json-logger 3.2.1** - JSON logging
- **uvicorn 0.34.0** - ASGI server

### DevOps & Deployment
- **Ansible** - Infrastructure automation
- **Docker** - Containerization
- **Google Sheets API** - Data backup

## 🔧 Features

### Core Functionality
- **Interactive Workout Tracking**: Step-by-step guided process for recording workouts
- **Exercise Categories**: Support for 8 muscle groups (Chest, Biceps, Back, Triceps, Shoulders, Forearms, Legs, Abs)
- **Comprehensive Exercise Database**: 100+ predefined exercises
- **Set Tracking**: Track up to 6 sets per exercise
- **Weight & Reps Recording**: Detailed weight (1kg - 180kg) and rep (1-20) tracking
- **Duplicate Prevention**: Prevents recording the same set twice on the same day
- **Training History Display**: Shows user's last training session for each exercise with detailed set/weight/reps breakdown
- **Personal Record (PR) Tracking**: Displays user's maximum weight achieved for each exercise with date

### User Experience
- **Inline Keyboard Navigation**: Easy-to-use button-based interface
- **Back Navigation**: Users can navigate back through previous selections
- **Progress Tracking**: Visual feedback on completed sets
- **Formatted Results**: Clean table format for workout summaries
- **Historical Context**: Automatic display of last training performance when selecting exercises
- **Personal Record Motivation**: Instant display of personal bests to encourage progression
- **First-time User Friendly**: Clear messaging for users who haven't done specific exercises before

### Data Management
- **PostgreSQL Storage**: Reliable primary data storage
- **Google Sheets Backup**: Optional backup for admin users
- **User Registration**: Automatic user registration on first interaction
- **Data Integrity**: Hash-based unique identifiers for training records
- **Training History Retrieval**: Efficient queries to fetch user-specific exercise history
- **Personal Record Calculation**: Optimized queries to find maximum weights across all training sessions
- **Session Grouping**: Smart grouping of training data by date for historical context

## 🏃‍♂️ Deployment Modes

The bot supports three deployment modes:

1. **Hybrid Mode** (`main.py`): Runs both polling and webhook simultaneously
2. **Long Polling** (`main_longpolling.py`): Traditional polling mode
3. **Webhook Mode** (`main_webhook.py`): Webhook-based with ngrok integration

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

-- Muscle groups
muscles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE         -- Muscle group name
)

-- Exercises
exercises (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255),               -- Exercise name
    muscle INT REFERENCES muscles(id), -- Associated muscle group
    UNIQUE(name, muscle)
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
- Telegram Bot Token
- Google Sheets API credentials (optional)

### Environment Variables
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
GOOGLE_SHEET_ID=your_sheet_id        # Optional
DATABASE_URL=postgres://myuser:mypassword@db:5432/gym_bot_db
```

### Docker Deployment
```bash
# Clone the repository
git clone <repository_url>
cd tg_gym_bot

# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Deploy with Docker Compose
docker-compose up -d
```

### Ansible Deployment
```bash
# Install Ansible dependencies
ansible-galaxy install -r ansible/requirements.yaml

# Set environment variables for deployment
export DOCKER_IMAGE=your_image
export DOCKER_TAG=latest
export TELEGRAM_BOT_TOKEN=your_token
export GOOGLE_SHEET_ID=your_sheet_id
export SERVER_ADDRESS=your_server_ip
export SERVER_USER=your_ssh_user
export SERVER_PORT=22

# Deploy
ansible-playbook -i ansible/inventory.yaml ansible/deploy.yaml
```

## 🎯 Usage

1. **Start the bot**: Send `/start` to initiate
2. **Begin workout**: Click "Record training" or send `/gym`
3. **Select muscle group**: Choose from 8 available categories
4. **Pick exercise**: Select from muscle-specific exercises
   - **NEW**: Bot automatically shows your last training history for this exercise
   - Shows formatted table with previous sets, weights, and reps
   - **NEW**: Displays your Personal Record (PR) - maximum weight ever lifted for this exercise
   - If first time doing exercise, shows friendly "You haven't done [exercise] before" message
5. **Choose set number**: Pick which set you're recording
6. **Enter weight**: Select weight used
7. **Enter reps**: Record number of repetitions
8. **Review**: Bot displays formatted summary and allows new entries

### Available Commands
- `/start` - Initialize bot and show main menu
- `/gym` - Start recording a new workout
- `/edit` - Access training editing options

### 📊 Training History & Personal Records Feature

When you select an exercise, the bot automatically displays your most recent training session and personal record:

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

Your PR: 80kg (10-12-2024)

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

## 🔒 Security Features

- **Input Validation**: All user inputs are validated against predefined options
- **SQL Injection Prevention**: Uses parameterized queries
- **Admin-only Backup**: Google Sheets backup restricted to specific user ID
- **Environment Variable Protection**: Sensitive data stored in environment variables

## 📊 Logging

The application uses structured JSON logging with the following levels:
- **INFO**: User actions, successful operations
- **ERROR**: Database errors, API failures
- **WARNING**: Validation issues, missing data

## 🚀 API Endpoints

When running in webhook mode:
- `POST /webhook` - Telegram webhook endpoint
- `POST /` - Alternative webhook endpoint (hybrid mode)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

## 🐛 Known Issues

- Webhook URL is hardcoded in `main_webhook.py` (line 29)
- Google Sheets integration requires manual service account setup
- Admin user ID is hardcoded for backup functionality

## 📞 Support

For issues and questions, please open an issue in the GitHub repository.
