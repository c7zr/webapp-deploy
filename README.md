# 🚀 SWATNFO Instagram Report Bot - Web Application

**Made by SWATNFO - d3sapiv2**

A powerful web-based Instagram reporting automation tool with modern UI and advanced features.

## ✨ Features

- 🎯 **11 Report Methods** - Spam, harassment, violence, nudity, and more
- ⚡ **Bulk Reporting** - Report up to 200 accounts simultaneously
- 🔒 **Secure Authentication** - JWT tokens, bcrypt hashing, AES-256 encryption
- 📊 **Real-time Analytics** - Track your reports with detailed statistics
- 👑 **Admin Dashboard** - Complete system management and user control
- 🌐 **d3sapiv2 API** - Enhanced backend with MongoDB and FastAPI
- 🎨 **Modern UI** - Sleek black and purple design with smooth animations

## 🚀 Quick Start

### Option 1: Automated Setup (Windows)

Double-click `start.bat` or run:
```bash
.\start.ps1
```

### Option 2: Manual Setup

1. **Install Python 3.8+**
   - Download from https://www.python.org/downloads/

2. **Install MongoDB**
   - Download from https://www.mongodb.com/try/download/community
   - Or use MongoDB Atlas (cloud)

3. **Install Dependencies**
   ```bash
   cd WebApp/backend
   pip install -r requirements.txt
   ```

4. **Start Backend**
   ```bash
   python main.py
   ```

5. **Open Frontend**
   - Open `WebApp/frontend/login.html` in your browser

## 🔑 Default Credentials

**Owner Account:**
- Username: `sw4t`
- Password: `SwAtNf0!2024#Pr0T3cT3d`
- Role: Owner (Protected)

## 📁 Project Structure

```
Project 7747/
├── WebApp/
│   ├── frontend/
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── dashboard.html
│   │   ├── reporting.html
│   │   ├── history.html
│   │   ├── settings.html
│   │   ├── about.html
│   │   ├── admin.html
│   │   ├── css/
│   │   │   └── styles.css
│   │   └── js/
│   │       ├── login.js
│   │       ├── register.js
│   │       ├── dashboard.js
│   │       ├── reporting.js
│   │       ├── history.js
│   │       ├── settings.js
│   │       ├── about.js
│   │       └── admin.js
│   └── backend/
│       ├── main.py
│       ├── requirements.txt
│       └── .env
├── start.bat
└── start.ps1
```

## 🎯 Report Methods

1. **Spam** - Repetitive or commercial content
2. **Self Injury** - Self-harm or suicide content
3. **Violent Threat** - Threats of violence
4. **Hate Speech** - Discriminatory content
5. **Nudity** - Inappropriate sexual content
6. **Bullying** - Harassment and bullying
7. **Impersonation (Me)** - Impersonating you
8. **TMNAOFCL** - Celebrity impersonation
9. **Sale of Illegal Goods** - Illegal products
10. **Violence** - Graphic violence
11. **Intellectual Property** - Copyright violations

## 🛡️ Security Features

- JWT token authentication with 7-day expiration
- bcrypt password hashing (12 rounds)
- AES-256 encryption for Instagram credentials
- Protected owner account (cannot be deleted)
- Role-based access control (User, Admin, Owner)
- CORS protection
- Rate limiting

## 🌐 API Endpoints

### Authentication
- `POST /v2/auth/register` - Register new user
- `POST /v2/auth/login` - Login user

### User
- `GET /v2/user/profile` - Get profile
- `PUT /v2/user/update` - Update profile
- `PUT /v2/user/password` - Change password
- `DELETE /v2/user/delete` - Delete account

### Credentials
- `GET /v2/credentials` - Get Instagram credentials
- `POST /v2/credentials` - Save credentials
- `POST /v2/credentials/test` - Test credentials

### Reporting
- `POST /v2/reports/send` - Send report
- `GET /v2/reports/stats` - Get statistics
- `GET /v2/reports/history` - Get history
- `DELETE /v2/reports/clear` - Clear history

### Admin
- `GET /v2/admin/stats` - System statistics
- `GET /v2/admin/users` - List users
- `PUT /v2/admin/config` - Update config
- `GET /v2/admin/logs` - System logs

## 🎨 Pages

1. **Login** - User authentication
2. **Register** - New account creation
3. **Dashboard** - Overview and statistics
4. **Reporting** - Single and bulk reporting
5. **History** - Report history with filters
6. **Settings** - Account and Instagram credentials
7. **About** - Information and documentation
8. **Admin** - System management (admin/owner only)

## 📊 Database Collections

- **users** - User accounts and authentication
- **credentials** - Encrypted Instagram credentials
- **reports** - Report logs and history
- **config** - System configuration
- **logs** - System activity logs

## 🔧 Configuration

Edit `WebApp/backend/.env` to customize:
- MongoDB connection URL
- API secrets and keys
- Rate limits and timeouts
- Default settings

## 📝 Getting Instagram Cookies

1. Open Instagram in your browser
2. Login to your account
3. Press F12 (Developer Tools)
4. Go to Application → Cookies → instagram.com
5. Copy `sessionid` and `csrftoken` values
6. Add them in Settings page

## ⚠️ Important Notes

- Use responsibly and in accordance with Instagram's Terms of Service
- This tool is for educational purposes
- Excessive reporting may result in account restrictions
- Keep your Instagram credentials secure

## 🆘 Troubleshooting

**Backend won't start:**
- Ensure Python 3.8+ is installed
- Check MongoDB is running
- Install dependencies: `pip install -r requirements.txt`

**Frontend not connecting:**
- Check backend is running on http://localhost:8000
- Verify CORS settings in backend
- Check browser console for errors

**Reports failing:**
- Test Instagram credentials in Settings
- Ensure sessionid and csrf_token are valid
- Check Instagram account isn't rate-limited

## 📞 Support

For issues or questions:
- Email: support@swatnfo.com
- Discord: SWATNFO#0001

## 📄 License

© 2025 SWATNFO. All rights reserved.

---

**Made by SWATNFO - d3sapiv2** 🚀
