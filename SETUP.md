# SciLib Setup Instructions

Follow these steps to get SciLib running on your local machine.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12 or higher  
- Git

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/SciLib.git
cd SciLib
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Setup PostgreSQL Database

First, create a PostgreSQL database and user:

```sql
-- Connect to PostgreSQL as superuser
psql -U postgres

-- Create database and user
CREATE DATABASE scilib_db;
CREATE USER scilib_user WITH PASSWORD 'scilib_password';
GRANT ALL PRIVILEGES ON DATABASE scilib_db TO scilib_user;

-- Exit psql
\q
```

### 5. Configure Environment Variables

The `.env` file is already configured for local development. Update the values if needed:

```bash
# Edit .env file if you want to change database credentials or API key
nano .env
```

### 6. Initialize Database

```bash
python -m app.database.init_db
```

You should see output confirming that all tables were created successfully.

### 7. Start the Application

```bash
uvicorn app.main:app --reload
```

The application will be available at:
- **Frontend**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Using the Application

### API Authentication

All API endpoints require authentication using the API key configured in your `.env` file. The frontend is already configured to use this key.

If you want to test the API directly, include the Authorization header:

```bash
curl -H "Authorization: Bearer scilib-demo-key-2024" http://localhost:8000/api/papers
```

### Frontend Usage

1. **Upload Papers**: Click the "Upload Paper" button to add PDF files
2. **Manage Collections**: Organize papers into collections  
3. **Create Tags**: Add tags to categorize papers
4. **Search**: Use the search box to find papers by title, authors, or abstract

### File Uploads

- Only PDF files are supported
- Maximum file size: 50MB
- Files are stored in the `uploads/` directory
- Metadata extraction will be implemented in Phase 2

## Development Workflow

### Working with Git Branches

```bash
# Create a new feature branch
git checkout -b feature/your-feature-name

# Make your changes and commit
git add .
git commit -m "feat: description of your changes"

# Push and create pull request
git push origin feature/your-feature-name
```

### Project Structure

```
SciLib/
├── app/                    # Backend application
│   ├── api/               # API endpoints
│   ├── database/          # Database models and connection
│   ├── main.py            # FastAPI application
│   ├── config.py          # Configuration settings
│   └── auth.py            # Authentication
├── static/                # Frontend files
│   ├── css/              # Stylesheets
│   ├── js/               # JavaScript files
│   └── index.html        # Main HTML file
├── uploads/              # Uploaded PDF files (created automatically)
├── requirements.txt      # Python dependencies
├── .env                 # Environment configuration
└── README.md            # Project documentation
```

## Troubleshooting

### Database Connection Issues

1. Ensure PostgreSQL is running:
   ```bash
   # macOS (with Homebrew)
   brew services start postgresql
   
   # Linux (systemd)
   sudo systemctl start postgresql
   
   # Check if it's running
   pg_isready
   ```

2. Verify database credentials in `.env` match your PostgreSQL setup

3. Test database connection:
   ```bash
   psql -h localhost -U scilib_user -d scilib_db
   ```

### Port Already in Use

If port 8000 is already in use, you can specify a different port:

```bash
uvicorn app.main:app --reload --port 8001
```

### Permission Issues with Uploads

Ensure the uploads directory has write permissions:

```bash
chmod 755 uploads/
```

## Next Steps

This completes Phase 1 of the SciLib project. Future phases will include:

- **Phase 2**: AI integration with LangChain for document summarization
- **Phase 3**: RAG system for intelligent document querying
- **Phase 4**: Advanced features like semantic search and recommendations

For questions or issues, check the project documentation or create an issue in the GitHub repository.