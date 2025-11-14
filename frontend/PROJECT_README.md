# Scribble Sense - Title Rating Application

A Quasar-based Vue 3 application for rating generated titles for text chunks.

## Features

- **Authentication**: Login functionality with JWT token-based authentication
- **Title Rating Interface**: Rate pairs of generated titles for text chunks
- **Progressive Rating**: Complete all rating pairs in a request before moving to the next
- **Automatic Submission**: Ratings are automatically submitted and a new task is loaded

## Setup

### Prerequisites

- Node.js (v16 or higher recommended)
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Configure the API URL:
   - Edit `.env` file and set the API_URL to your backend server
   - Default: `API_URL=http://localhost:8000`

### Development

Run the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:9000` (or the port specified by Quasar).

### Production Build

Build the application for production:
```bash
npm run build
```

## Usage

### Login

1. Navigate to the login page (automatically shown if not authenticated)
2. Enter your email and password
3. Click "Login"

### Rating Titles

Once logged in, the application will:

1. **Load a rating request** from the API (`GET /api/rating/request`)
2. **Display the chunk text** at the top of the page
3. **Show progress** indicating how many title pairs have been rated
4. For each pair of titles:
   - Display the query used to generate the titles
   - Show both generated titles
   - Allow you to rate each title as "Irrelevant", "Nonsense", or "Relevant"
   - Allow you to select exactly one preferred title
   - Click "DONE" when finished rating the pair

5. After all pairs are rated, the response is automatically submitted (`POST /api/rating/response`)
6. The next rating request is automatically loaded

### Logout

Click the "Logout" button in the header to log out and return to the login page.

## API Integration

The application integrates with the following API endpoints:

- `POST /auth/jwt/login` - User authentication
- `POST /auth/jwt/logout` - User logout
- `GET /users/me` - Get current user information
- `GET /api/rating/request` - Get a rating request
- `POST /api/rating/response` - Submit completed ratings

## Data Models

### RatingRequest
- Contains a chunk of text and multiple title pairs to rate
- Each title pair contains two titles generated with different parameters

### RatingResponse
- Contains all ratings for a single request
- Each rating includes:
  - Both titles with their ratings (irrelevant, nonsense, relevant)
  - Which title was preferred
  - Start and end time for the rating

## Project Structure

```
src/
├── boot/           # Quasar boot files (axios configuration)
├── components/     # Reusable Vue components
├── layouts/        # Layout components (MainLayout with header)
├── pages/          # Page components (LoginPage, RatingPage)
├── router/         # Vue Router configuration
├── services/       # API service layer
├── stores/         # Pinia stores (auth-store)
└── types/          # TypeScript type definitions
```

## Environment Variables

- `API_URL` - Backend API base URL (default: `http://localhost:8000`)

## Technologies Used

- **Quasar Framework** - Vue.js framework
- **Vue 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Pinia** - State management
- **Axios** - HTTP client
- **Vue Router** - Routing
- **UUID** - Unique ID generation
