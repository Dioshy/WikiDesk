# 📞 WikiDesk - Système de Gestion des Appels

Un système complet de gestion et suivi des appels téléphoniques et des actes de gestion pour les professionnels de l'assurance.

## Features

### 🚀 Core Functionality
- **User Management**: Role-based access control (Admin/Standard User)
- **Time Tracking**: Log minutes spent on client interactions
- **Real-time Updates**: WebSocket-powered live updates
- **Offline Mode**: Local storage with auto-sync when back online
- **Modern UI**: Responsive design inspired by modern cloud interfaces

### 📊 Reporting & Analytics
- **Excel Exports**: Daily, monthly, and yearly reports
- **Multiple Sheets**: Summary, detailed entries, user stats, courtier breakdown
- **Custom Reports**: Date range selection with various filters
- **Live Dashboard**: Real-time statistics and charts

### 🔒 Data Protection
- **Automatic Backups**: Daily scheduled backups with rotation
- **Manual Backup**: On-demand backup creation
- **Multiple Database Support**: SQLite, PostgreSQL, MySQL

### 📱 User Experience
- **Responsive Design**: Works on desktop, tablet, and mobile
- **Dark Mode Support**: User preference toggle
- **Live Clock**: Real-time date/time display
- **Flash Messages**: User feedback for all actions

## Tech Stack

- **Backend**: Python 3.8+, Flask 3.0
- **Database**: PostgreSQL (production) / SQLite (development)
- **Frontend**: HTML5, CSS3, JavaScript ES6+
- **Real-time**: WebSockets (Socket.IO)
- **Charts**: Chart.js
- **Export**: pandas, openpyxl
- **Styling**: Custom CSS with modern gradients and animations

## Installation

### 1. Prerequisites
```bash
# Python 3.8 or higher
python --version

# PostgreSQL (for production)
psql --version

# Git
git --version
```

### 2. Clone and Setup
```bash
# Clone repository
git clone <repository-url>
cd minutes-tracker

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings
# Set DATABASE_URL, SECRET_KEY, etc.
```

### 4. Database Setup
```bash
# Initialize database
flask init-db

# Create admin user and sample data
flask create-admin

# Run migrations (if needed)
flask db upgrade
```

### 5. Run Application
```bash
# Development mode
python run.py

# Or using Flask CLI
flask run --host=0.0.0.0 --port=5000
```

## Configuration

### Environment Variables
```bash
SECRET_KEY=your-secret-key-here
DATABASE_URL=postgresql://username:password@localhost:5432/minutes_tracker
BACKUP_PATH=./backups
DEBUG=True
FLASK_ENV=development
```

### Database URLs
```bash
# SQLite (Development)
DATABASE_URL=sqlite:///minutes_tracker.db

# PostgreSQL (Production)
DATABASE_URL=postgresql://user:password@localhost:5432/minutes_tracker

# MySQL
DATABASE_URL=mysql://user:password@localhost:3306/minutes_tracker
```

## Usage

### Initial Setup
1. **Admin Login**: Use credentials created during setup
2. **Add Users**: Navigate to Admin → Users → Add User
3. **Add Courtiers**: Navigate to Admin → Courtiers
4. **Configure Backup**: Set up automatic backup schedule

### Daily Operations
1. **Log Minutes**: Use dashboard quick-add form
2. **View Stats**: Real-time dashboard updates
3. **Generate Reports**: Admin → Reports for Excel exports
4. **Manage Data**: Admin panel for user/courtier management

### Backup & Restore
```bash
# Manual backup
flask create-backup

# List backups
flask list-backups

# Restore backup
flask restore-backup backup_file.gz
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `GET /auth/logout` - User logout
- `POST /auth/register` - Create user (admin only)

### Entries
- `GET /api/entries` - Get entries (with filters)
- `POST /api/entries` - Create new entry
- `PUT /api/entries/<id>` - Update entry
- `DELETE /api/entries/<id>` - Delete entry

### Stats
- `GET /api/stats` - User dashboard stats
- `GET /api/chart-data` - Chart data for graphs

### Admin
- `GET /admin/api/live-stats` - Real-time admin statistics
- `GET /admin/export/<period>` - Export reports

## Deployment

### Local Network Deployment
1. **Set Production Config**:
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY="your-production-secret"
   export DATABASE_URL="postgresql://..."
   ```

2. **Use Production Server**:
   ```bash
   # Install production server
   pip install gunicorn

   # Run with gunicorn
   gunicorn -w 4 -b 0.0.0.0:5000 run:app
   ```

3. **Configure Reverse Proxy** (Optional):
   - Use Nginx or Apache for static files
   - Set up SSL certificates for HTTPS

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "run:app"]
```

## Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: User email address
- `password_hash`: Encrypted password
- `full_name`: Display name
- `role`: 'admin' or 'user'
- `is_active`: Account status
- `created_at`: Registration date
- `last_login`: Last login timestamp

### Entries Table
- `id`: Primary key
- `date`: Entry date
- `time`: Entry time
- `period`: Period (YYYYMM format)
- `user_id`: Foreign key to users
- `courtier_id`: Foreign key to courtiers
- `minutes`: Duration in minutes
- `acte_type`: Activity type enum
- `dossier`: Case/file number
- `client_name`: Client name
- `description`: Additional details

### Courtiers Table
- `id`: Primary key
- `name`: Courtier name
- `odoo_so_id`: Odoo integration ID
- `is_active`: Status flag
- `created_at`: Creation date

## Troubleshooting

### Common Issues

1. **Database Connection Error**:
   ```bash
   # Check DATABASE_URL format
   # Ensure database server is running
   # Verify credentials
   ```

2. **Permission Denied**:
   ```bash
   # Check file permissions
   chmod +x run.py
   
   # Check backup directory
   mkdir -p backups
   chmod 755 backups
   ```

3. **Import Errors**:
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

4. **Static Files Not Loading**:
   ```bash
   # Check file paths in templates
   # Ensure Flask app serves static files
   # Verify CSS/JS file permissions
   ```

### Performance Optimization

1. **Database Indexing**: Automatic indexes on frequently queried columns
2. **Connection Pooling**: Configured for production databases
3. **Caching**: Browser caching for static assets
4. **Compression**: Gzip compression for backup files

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is proprietary software for internal company use.

## Support

For technical support or feature requests, please contact the system administrator.

---

## Version History

### v1.0.0 (Current)
- Initial release
- Core time tracking functionality
- Admin panel and user management
- Excel export capabilities
- Real-time updates
- Offline mode support
- Automatic backup system