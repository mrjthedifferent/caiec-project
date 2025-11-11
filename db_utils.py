import mysql.connector
from mysql.connector import Error
from typing import Optional, Dict, List
import csv
import os
import io

class DatabaseManager:
    def __init__(self, host: str = "localhost", port: int = 3306, 
                 user: str = "root", password: str = "12345678", 
                 database: str = "employee_db"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None
    
    def connect(self, use_database: bool = True):
        """Connect to MySQL server"""
        try:
            if use_database:
                self.connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    database=self.database
                )
            else:
                # Connect without specifying database (for initial setup)
                self.connection = mysql.connector.connect(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password
                )
            
            if self.connection.is_connected():
                print(f"Successfully connected to MySQL server")
                return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")
    
    def create_database(self):
        """Create the employee database if it doesn't exist"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            print(f"Database '{self.database}' created or already exists")
            cursor.close()
            return True
        except Error as e:
            print(f"Error creating database: {e}")
            return False
    
    def create_table(self):
        """Create the employees table"""
        try:
            cursor = self.connection.cursor()
            create_table_query = """
            CREATE TABLE IF NOT EXISTS employees (
                EmployeeID VARCHAR(20) PRIMARY KEY,
                Name VARCHAR(255) NOT NULL,
                Email VARCHAR(255),
                Phone VARCHAR(50),
                Department VARCHAR(100),
                Position VARCHAR(100),
                JoinDate DATE,
                SalaryUSD DECIMAL(10, 2),
                INDEX idx_employee_id (EmployeeID),
                INDEX idx_name (Name),
                INDEX idx_department (Department)
            )
            """
            cursor.execute(create_table_query)
            self.connection.commit()
            print("Table 'employees' created or already exists")
            cursor.close()
            return True
        except Error as e:
            print(f"Error creating table: {e}")
            return False
    
    def import_from_csv(self, csv_file: str = "knowledge.txt"):
        """Import employee data from CSV file"""
        if not os.path.exists(csv_file):
            print(f"File '{csv_file}' not found")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Clear existing data
            cursor.execute("DELETE FROM employees")
            
            # Read and parse CSV
            with open(csv_file, 'r', encoding='utf-8') as f:
                # Read all lines and filter out empty ones
                all_lines = f.readlines()
                # Filter out empty lines and create a string buffer
                filtered_lines = [line for line in all_lines if line.strip()]
                csv_content = ''.join(filtered_lines)
                reader = csv.DictReader(io.StringIO(csv_content))
                
                insert_query = """
                INSERT INTO employees 
                (EmployeeID, Name, Email, Phone, Department, Position, JoinDate, SalaryUSD)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                Name = VALUES(Name),
                Email = VALUES(Email),
                Phone = VALUES(Phone),
                Department = VALUES(Department),
                Position = VALUES(Position),
                JoinDate = VALUES(JoinDate),
                SalaryUSD = VALUES(SalaryUSD)
                """
                
                rows_inserted = 0
                for row in reader:
                    # Skip rows without EmployeeID
                    if not row.get('EmployeeID') or not row.get('EmployeeID').strip():
                        continue
                    
                    # Parse date
                    join_date = row.get('JoinDate', '').strip()
                    if not join_date:
                        join_date = None
                    
                    # Parse salary
                    salary = row.get('SalaryUSD', '').strip()
                    if not salary:
                        salary = None
                    else:
                        try:
                            salary = float(salary)
                        except ValueError:
                            salary = None
                    
                    values = (
                        row.get('EmployeeID', '').strip(),
                        row.get('Name', '').strip(),
                        row.get('Email', '').strip(),
                        row.get('Phone', '').strip(),
                        row.get('Department', '').strip(),
                        row.get('Position', '').strip(),
                        join_date,
                        salary
                    )
                    
                    cursor.execute(insert_query, values)
                    rows_inserted += 1
                
                self.connection.commit()
                print(f"Imported {rows_inserted} employee records")
                cursor.close()
                return True
                
        except Error as e:
            print(f"Error importing data: {e}")
            if self.connection:
                self.connection.rollback()
            return False
    
    def get_employee_by_id(self, employee_id: str) -> Optional[Dict]:
        """Get employee information by EmployeeID"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM employees WHERE EmployeeID = %s"
            cursor.execute(query, (employee_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
        except Error as e:
            print(f"Error querying employee: {e}")
            return None
    
    def search_employees(self, search_term: str, limit: int = 10) -> List[Dict]:
        """Search employees by name, email, or department"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = """
            SELECT * FROM employees 
            WHERE Name LIKE %s 
               OR Email LIKE %s 
               OR Department LIKE %s
               OR EmployeeID LIKE %s
            LIMIT %s
            """
            search_pattern = f"%{search_term}%"
            cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern, limit))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            print(f"Error searching employees: {e}")
            return []
    
    def get_all_employees(self, limit: int = 100) -> List[Dict]:
        """Get all employees"""
        try:
            cursor = self.connection.cursor(dictionary=True)
            query = "SELECT * FROM employees LIMIT %s"
            cursor.execute(query, (limit,))
            results = cursor.fetchall()
            cursor.close()
            return results
        except Error as e:
            print(f"Error fetching employees: {e}")
            return []

