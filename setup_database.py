"""
Database setup script to create employee database and import data
"""
from db_utils import DatabaseManager
import sys

def setup_database():
    """Setup the employee database"""
    print("Starting database setup...")
    
    # Initialize database manager without database (to create it first)
    db_manager = DatabaseManager()
    
    # Connect without database
    if not db_manager.connect(use_database=False):
        print("Failed to connect to MySQL server")
        sys.exit(1)
    
    # Create database
    if not db_manager.create_database():
        print("Failed to create database")
        db_manager.disconnect()
        sys.exit(1)
    
    # Disconnect and reconnect with database
    db_manager.disconnect()
    
    # Reconnect with database
    if not db_manager.connect(use_database=True):
        print("Failed to connect to database")
        sys.exit(1)
    
    # Create table
    if not db_manager.create_table():
        print("Failed to create table")
        db_manager.disconnect()
        sys.exit(1)
    
    # Import data
    if not db_manager.import_from_csv("knowledge.txt"):
        print("Failed to import data")
        db_manager.disconnect()
        sys.exit(1)
    
    print("\nDatabase setup completed successfully!")
    db_manager.disconnect()

if __name__ == "__main__":
    setup_database()


