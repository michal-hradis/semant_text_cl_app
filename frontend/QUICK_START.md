# Quick Start Guide

## Running the Application

### Development Mode

```bash
# Start the development server
npm run dev
```

The application will be available at `http://localhost:9000` (or another port if 9000 is busy).

### Building for Production

```bash
# Build the application
npm run build
```

The built files will be in the `dist/spa` directory.

## Testing the Application

If you don't have a backend running yet, here's what you need to know:

### Required Backend Endpoints

1. **POST /auth/jwt/login**
   - Body: `username=<email>&password=<password>` (form-urlencoded)
   - Returns: `{ "access_token": "...", "token_type": "bearer" }`

2. **GET /users/me**
   - Headers: `Authorization: Bearer <token>`
   - Returns: User information

3. **GET /api/rating/request**
   - Headers: `Authorization: Bearer <token>`
   - Returns: RatingRequest object with chunk and titles_lists

4. **POST /api/rating/response**
   - Headers: `Authorization: Bearer <token>`
   - Body: RatingResponseNew object
   - Returns: Success confirmation

### Setting Up Backend URL

Edit the `.env` file:

```env
API_URL=http://localhost:8000
```

Or for a different backend:

```env
API_URL=https://your-backend-api.com
```

## Troubleshooting

### CORS Issues

If you get CORS errors, your backend needs to allow requests from the frontend origin. Add CORS headers on the backend:

```python
# Example for FastAPI
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:9000"],  # Add your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Authentication Not Working

1. Check that the API_URL in `.env` is correct
2. Verify the backend is running
3. Check browser console for error messages
4. Verify credentials are correct

### Cannot Load Rating Requests

1. Ensure you're logged in
2. Check that the backend has rating requests available
3. Verify the `/api/rating/request` endpoint is accessible
4. Check browser network tab for API response

## Code Structure

```
src/
├── pages/
│   ├── LoginPage.vue       # Login form
│   └── RatingPage.vue      # Main rating interface
├── stores/
│   └── auth-store.ts       # Authentication state
├── services/
│   └── api.ts             # API calls
├── types/
│   └── api.ts             # TypeScript types
├── router/
│   ├── index.ts           # Router with auth guards
│   └── routes.ts          # Route definitions
└── boot/
    └── axios.ts           # HTTP client setup
```

## Next Steps

1. **Customize Styling**: Edit Quasar theme in `src/css/quasar.variables.scss`
2. **Add More Features**: Such as user statistics, rating history, etc.
3. **Add Tests**: Create unit tests for components and stores
4. **Deploy**: Build for production and deploy to your server

## Useful Commands

```bash
# Development
npm run dev              # Start dev server
npm run lint             # Run linter
npm run format           # Format code with Prettier

# Production
npm run build            # Build for production
```

## Support

For Quasar-specific documentation: https://quasar.dev
