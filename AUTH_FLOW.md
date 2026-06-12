# Azure AI Ops Auth Flow

## Sequence

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant FE as React SPA
    participant MS as Microsoft Entra ID
    participant BE as FastAPI Backend
    participant DB as Postgres

    U->>FE: Click "Sign in with Microsoft"
    FE->>FE: AuthProvider.login()\n[frontend/src/app/providers/AuthProvider.tsx]
    FE->>MS: loginRedirect()\n[frontend/src/services/msal.ts]\nclientId = VITE_ENTRA_CLIENT_ID\nauthority = https://login.microsoftonline.com/VITE_ENTRA_TENANT_ID\nredirectUri = VITE_ENTRA_REDIRECT_URI
    MS-->>FE: Redirect back to /auth/callback
    FE->>FE: handleRedirectPromise()\n[frontend/src/app/providers/AuthProvider.tsx]
    FE->>MS: acquireTokenSilent()\nscopes = [VITE_ENTRA_API_SCOPE]
    FE->>BE: GET /api/v1/me\nAuthorization: Bearer <token>\n[frontend/src/services/api.ts]
    BE->>BE: HTTPBearer + get_current_user()\n[backend/app/auth/dependencies.py]
    BE->>BE: validate_token()\n[backend/app/auth/jwt_validator.py]\nENTRA_TENANT_ID + ENTRA_CLIENT_ID from backend/.env
    BE->>DB: find/create user
    DB-->>BE: user row
    BE-->>FE: UserInfo JSON\n[backend/app/api/auth.py]

    FE->>BE: POST /api/v1/chat/session
    BE->>DB: create session\n[backend/app/api/chat.py]
    BE-->>FE: session_id

    FE->>BE: POST /api/v1/chat/message
    BE->>BE: resolve tool + history\n[backend/app/services/chat_service.py]\n[backend/app/services/tool_resolver.py]
    BE-->>FE: ChatResponse
```

## Env Vars

### Frontend

- `VITE_MOCK_AUTH=false`
- `VITE_ENTRA_CLIENT_ID`
  - Frontend SPA app registration client ID
- `VITE_ENTRA_TENANT_ID`
  - Entra tenant / directory ID
- `VITE_ENTRA_API_SCOPE`
  - Backend API scope, for example `api://<backend-client-id>/access_as_user`
- `VITE_ENTRA_REDIRECT_URI`
  - Usually `http://localhost:5173/auth/callback`
- `VITE_ENTRA_SCOPES`
  - Optional extra scopes

### Backend

- `ENTRA_TENANT_ID`
  - Same tenant / directory ID
- `ENTRA_CLIENT_ID`
  - Backend API app registration client ID
- `DEV_BYPASS_AUTH=true`
  - Local development only

## File Map

### Frontend

- [frontend/src/services/msal.ts](frontend/src/services/msal.ts)
- [frontend/src/app/providers/AuthProvider.tsx](frontend/src/app/providers/AuthProvider.tsx)
- [frontend/src/features/auth/LoginPage.tsx](frontend/src/features/auth/LoginPage.tsx)
- [frontend/src/features/auth/AuthCallbackPage.tsx](frontend/src/features/auth/AuthCallbackPage.tsx)
- [frontend/src/services/api.ts](frontend/src/services/api.ts)
- [frontend/src/services/authStorage.ts](frontend/src/services/authStorage.ts)

### Backend

- [backend/app/auth/dependencies.py](backend/app/auth/dependencies.py)
- [backend/app/auth/jwt_validator.py](backend/app/auth/jwt_validator.py)
- [backend/app/api/auth.py](backend/app/api/auth.py)
- [backend/app/api/chat.py](backend/app/api/chat.py)
- [backend/app/api/approvals.py](backend/app/api/approvals.py)
- [backend/app/services/chat_service.py](backend/app/services/chat_service.py)
- [backend/app/services/tool_resolver.py](backend/app/services/tool_resolver.py)

## Short Explanation

1. User clicks sign in on the frontend.
2. React uses the frontend app registration to start Microsoft login.
3. Entra redirects back to the frontend callback route.
4. React requests a token for the backend API scope.
5. React sends the token to FastAPI.
6. FastAPI validates the token using the backend app registration and tenant.
7. If valid, the backend creates/loads the user and serves chat/session/approval data.

