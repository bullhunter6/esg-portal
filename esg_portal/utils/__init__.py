# This file is intentionally left empty to make the directory a Python package.

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Get a connection to the database"""
    DB_NAME = "postgres"
    DB_USER = "postgres"
    DB_PASS = "finvizier2023"
    DB_HOST = "esgarticles.cf4iaa2amdt3.me-central-1.rds.amazonaws.com"
    DB_PORT = "5432"
    
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )
    return conn 

# ESG Portal Utilities Package 

"""
Utility functions for ESG Portal
""" 