# Gym Progress Analytics Website

A comprehensive Next.js gym analytics platform featuring GitHub-style activity tracking, exercise statistics, and muscle group distribution charts, integrated with Telegram authentication and PostgreSQL database.

## Features

### 🏠 Dashboard & Activity Tracking
- 📊 GitHub-style contribution grid showing daily training intensity
- 🔥 Weekly streak tracking and activity statistics
- 📅 Monday-first week layout with Georgian timezone support (+4 GMT)
- 🎯 2x2 stats dashboard with total exercises, sets, and personal records

### 📈 Exercise Analytics
- 📊 Interactive exercise progress charts with Apache ECharts
- 🏋️ Detailed statistics pages for each muscle group and exercise
- 📈 Multiple series visualization for different sets (Set 1, Set 2, etc.)
- 🎯 Personal records tracking and progression analysis

### 💪 Muscle Group Distribution
- 📊 Weekly muscle sets distribution charts (6-month overview)
- 📈 Full-year detailed distribution view with 12-month data
- 🎨 Gradient stacked area charts with responsive design
- 📱 Mobile-optimized with orientation hints

### 🔐 Authentication & Navigation
- 🔑 Telegram Login Widget integration with NextAuth.js
- 🍔 Professional burger menu navigation system
- 👤 User profile access with photo display
- 🔒 Session-based authentication and authorization

## Technology Stack

- **Next.js 15.1.1** - React framework with standalone output
- **TypeScript** - Type safety and development experience
- **Apache ECharts 5.4.3** - Data visualization and charting
- **TailwindCSS** - Utility-first CSS framework
- **NextAuth.js** - Authentication with Telegram provider
- **PostgreSQL** - Database (shared with gym bot)
- **Telegram Login Widget** - OAuth integration

## Pages & Routes

- **`/`** - Main dashboard with activity grid and stats
- **`/profile`** - User profile page with GitHub-style activity
- **`/exercises`** - Exercise list grouped by muscle groups
- **`/exercises/[muscle]/[exercise]`** - Detailed exercise statistics
- **`/sets-distribution`** - Full-year muscle group distribution

## API Endpoints

- **`GET /api/user-activity`** - Daily training data for activity grid
- **`GET /api/user-stats`** - Overall user statistics
- **`GET /api/muscle-groups`** - List of muscle groups with exercise counts
- **`GET /api/exercises/[muscle]`** - Exercises for specific muscle group
- **`GET /api/exercises/[muscle]/[exercise]`** - Exercise progress data
- **`GET /api/muscle-sets-weekly`** - 6-month muscle sets distribution
- **`GET /api/muscle-sets-weekly-full`** - 12-month muscle sets distribution

## Development

1. **Environment Setup:**
```bash
cp .env.example .env.local
# Edit .env.local with your database credentials
```

2. **Install dependencies:**
```bash
npm install
```

3. **Run development server:**
```bash
npm run dev
```

4. **Open [http://localhost:3000](http://localhost:3000)**

## Environment Variables

Create `.env.local` based on `.env.example`:

```bash
# NextAuth.js Configuration
NEXTAUTH_URL=https://gymbot.olykov.com
NEXTAUTH_SECRET=your-nextauth-secret-key-here

# Telegram Bot Configuration  
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
NEXT_PUBLIC_TELEGRAM_BOT_USERNAME=your_bot_username

# Database Configuration
DB_USER=myuser
DB_HOST=your-database-host
DB_NAME=gymbot_db
DB_PASSWORD=your-database-password
DB_PORT=5432
```

## Database Connection

The site connects to the gym bot PostgreSQL database with timezone-aware date handling:
- **Georgian Timezone**: UTC+4 with proper date string extraction
- **Tables**: `trainings`, `exercises`, `muscles`
- **Key Fields**: `date`, `user_id`, `muscle`, `exercise`, `sets`

## Chart Features

### Activity Grid (GitHub-style)
- **Layout**: Monday-first week layout (7x53 grid)
- **Colors**: Intensity-based (0-4+ sets per day)
- **Tooltips**: Date and set count information
- **Navigation**: Clickable cells for detailed views

### Exercise Progress Charts  
- **X-axis**: Training dates (DD/MM format)
- **Y-axis**: Weight in kg
- **Series**: Multiple lines per set number
- **Interactions**: Zoom, pan, save image
- **Responsive**: Mobile-optimized layouts

### Muscle Distribution Charts
- **Type**: Stacked area charts with gradients
- **Data**: Weekly aggregated sets by muscle group
- **Legend**: Scrollable for >6 muscle groups
- **Timeframes**: 6-month overview + 12-month detailed

## Deployment

### Production Build
```bash
npm run build
npm start
```

### Docker Deployment
```bash
# Multi-stage optimized build
docker build -t gym-bot-frontend .
docker run -p 3333:3000 gym-bot-frontend
```

### CI/CD Integration
- **GitHub Actions**: Automated builds on main branch
- **Docker Hub**: `gym-bot-frontend` image with timestamp tags
- **Ansible**: Automated deployment with docker-compose

## Architecture

- **Standalone Output**: Next.js optimized for containerization
- **Server Components**: API routes with PostgreSQL integration  
- **Client Components**: Interactive charts and authentication
- **Session Management**: NextAuth.js with Telegram provider
- **Responsive Design**: Mobile-first with TailwindCSS

## Performance Optimizations

- **Multi-stage Docker**: ~70% smaller production images
- **Static Generation**: Pre-built pages where possible
- **Image Optimization**: Next.js built-in optimization
- **Chart Loading**: Lazy loading and responsive breakpoints
- **Database Queries**: Optimized with proper indexing