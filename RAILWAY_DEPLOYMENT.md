# Railway Deployment Notes

Use separate Railway services for the backend and frontend.

## Backend service variables

Set these on the backend service:

- `ENVIRONMENT=production`
- `OPENAI_API_KEY`
- `DATABASE_URL`
- `REDIS_URL`
- `ENTRA_TENANT_ID`
- `ENTRA_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_SUBSCRIPTION_ID`
- `CORS_ORIGINS` with the deployed frontend origin, for example `https://frontend-prod.up.railway.app`
- Optional: `ALLOWED_USER_EMAILS`, `ADMIN_USER_EMAILS`, `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION`, `AZURE_SPEECH_LANGUAGE`

## Frontend service variables

Set these on the frontend service:

- `VITE_API_BASE_URL` pointing to the backend API, for example `https://backend-prod.up.railway.app/api/v1`
- `VITE_MOCK_AUTH=false`
- `VITE_ENTRA_CLIENT_ID`
- `VITE_ENTRA_TENANT_ID`
- `VITE_ENTRA_REDIRECT_URI` pointing to the deployed frontend callback URL, for example `https://frontend-prod.up.railway.app/auth/callback`
- `VITE_ENTRA_API_SCOPE`
- Optional: `VITE_ENTRA_SCOPES`

## Reference files

- [Backend example env](./.env.railway.example)
- [Frontend example env](./frontend/.env.railway.example)
- [Backend Dockerfile](./backend/Dockerfile)
- [Frontend Dockerfile](./frontend/Dockerfile)
