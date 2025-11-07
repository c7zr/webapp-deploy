# SWATNFO Instagram Report Bot - Backend

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install MongoDB

Download and install MongoDB Community Edition:
- Windows: https://www.mongodb.com/try/download/community
- Or use MongoDB Atlas (cloud): https://www.mongodb.com/atlas

### 3. Configure Environment

Edit `.env` file and update:
- SECRET_KEY (generate a secure random key)
- MONGODB_URL (if using custom MongoDB setup)
- Other settings as needed

### 4. Run the Backend

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the API

- API Base URL: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## API Endpoints

### Authentication
- POST `/v2/auth/register` - Register new user
- POST `/v2/auth/login` - Login user

### User Management
- GET `/v2/user/profile` - Get user profile
- PUT `/v2/user/update` - Update user profile
- PUT `/v2/user/password` - Change password
- DELETE `/v2/user/delete` - Delete account

### Credentials
- GET `/v2/credentials` - Get Instagram credentials
- POST `/v2/credentials` - Save Instagram credentials
- POST `/v2/credentials/test` - Test credentials

### Reporting
- POST `/v2/reports/send` - Send single report
- GET `/v2/reports/stats` - Get user statistics
- GET `/v2/reports/recent` - Get recent reports
- GET `/v2/reports/history` - Get report history
- DELETE `/v2/reports/clear` - Clear history

### Admin (Requires admin/owner role)
- GET `/v2/admin/stats` - System statistics
- GET `/v2/admin/users` - List all users
- GET `/v2/admin/users/{id}` - Get user details
- PUT `/v2/admin/users/{id}` - Update user
- DELETE `/v2/admin/users/{id}` - Delete user
- GET `/v2/admin/reports` - All system reports
- GET `/v2/admin/config` - System configuration
- PUT `/v2/admin/config` - Update configuration
- GET `/v2/admin/logs` - System logs
- DELETE `/v2/admin/logs` - Clear logs

## Default Accounts

### Owner Account
- Username: `sw4t`
- Password: `SwAtNf0!2024#Pr0T3cT3d`
- Role: Owner (protected, cannot be deleted)

## Security Features

- JWT token authentication
- bcrypt password hashing (12 rounds)
- AES-256 encryption for Instagram credentials
- CORS protection
- Rate limiting
- Protected owner account

## Database Schema

### Users Collection
- _id (string): User ID
- username (string): Username
- email (string): Email address
- password (string): Hashed password
- role (string): user/admin/owner
- isActive (boolean): Account status
- isProtected (boolean): Protection flag
- createdAt (datetime): Registration date
- reportCount (number): Total reports sent

### Credentials Collection
- userId (string): User ID
- sessionId (string): Encrypted Instagram session ID
- csrfToken (string): Encrypted CSRF token
- updatedAt (datetime): Last update

### Reports Collection
- userId (string): User ID
- username (string): Username
- target (string): Target username
- targetId (string): Target Instagram ID
- method (string): Report method
- status (string): success/failed
- type (string): single/bulk
- timestamp (datetime): Report time

### Config Collection
- _id: "system"
- maxReportsPerUser (number)
- maxBulkTargets (number)
- apiTimeout (number)
- rateLimitPerMinute (number)
- maintenanceMode (boolean)
- registrationEnabled (boolean)

### Logs Collection
- timestamp (datetime)
- level (string): info/warning/error
- message (string)
- details (object)

## Made by SWATNFO - d3sapiv2
