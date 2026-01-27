#!/usr/bin/env python3
"""Initialize database with tables and seed data"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import get_database
from src.common.logger import get_logger

logger = get_logger(__name__)

def init_database():
    """Create all tables"""
    logger.info("Initializing database...")
    
    db = get_database()
    db.create_tables()
    
    logger.info("✅ Database tables created successfully")

if __name__ == "__main__":
    init_database()