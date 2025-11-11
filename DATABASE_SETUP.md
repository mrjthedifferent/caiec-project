# Database Setup Guide

This guide explains how to set up the MySQL database for the employee RAG system.

## Prerequisites

1. MySQL Server installed and running
2. Python dependencies installed: `pip install -r requirements.txt`

## Database Credentials

The system uses the following default credentials (configured in `db_utils.py`):
- **Host**: localhost
- **Port**: 3306
- **User**: root
- **Password**: 12345678
- **Database**: employee_db

## Setup Steps

### 1. Ensure MySQL is Running

Make sure your MySQL server is running and accessible with the credentials above.

### 2. Run the Database Setup Script

```bash
python setup_database.py
```

This script will:
- Connect to MySQL server
- Create the `employee_db` database
- Create the `employees` table with proper schema
- Import all employee data from `knowledge.txt

### 3. Verify the Setup

You can verify the setup by checking the database:

```sql
USE employee_db;
SELECT COUNT(*) FROM employees;
SELECT * FROM employees LIMIT 5;
```

## Usage

### Query by Employee ID in RAG

The RAG service now automatically detects employee IDs in queries and queries the database. Examples:

**Via API Query Endpoint:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "Tell me about employee EMP001"}'
```

**Via Direct Employee Endpoint:**
```bash
curl http://localhost:8000/employee/EMP001
```

### Supported Query Formats

The system recognizes employee IDs in various formats:
- `EMP001`
- `userId EMP001`
- `employee id EMP001`
- `ID EMP001`

## API Endpoints

### GET `/employee/{employee_id}`

Get employee information directly by EmployeeID.

**Example:**
```bash
GET /employee/EMP001
```

**Response:**
```json
{
  "answer": "Employee EMP001 is William Moore...",
  "employee_data": {
    "EmployeeID": "EMP001",
    "Name": "William Moore",
    "Email": "daniel28@williams-king.com",
    ...
  }
}
```

### POST `/query`

Query the RAG system. If the query contains an employee ID, it will automatically query the database.

**Example:**
```bash
POST /query
{
  "query": "What is the salary of EMP001?",
  "max_chunks": 3
}
```

## Troubleshooting

### Database Connection Error

If you see "Could not connect to database", check:
1. MySQL server is running
2. Credentials in `db_utils.py` are correct
3. MySQL user has proper permissions

### Employee Not Found

If an employee ID is not found:
1. Verify the employee exists in the database
2. Check the EmployeeID format (should be EMP###)
3. Re-run `setup_database.py` to re-import data

### Re-importing Data

To re-import data from `knowledge.txt`:

```bash
python setup_database.py
```

This will clear existing data and re-import from the CSV file.


