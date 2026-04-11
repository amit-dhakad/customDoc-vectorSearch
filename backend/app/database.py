from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

"""
backend/app/database.py — SQLAlchemy Connection & Session Management

ARCHITECTURE OVERVIEW
─────────────────────────────────────────────────────────────────────────────
This module serves as the foundational data persistence layer. It establishes 
the connection between the FastAPI application and the SQLite database layer. 

THE SESSION-PER-REQUEST PATTERN
─────────────────────────────────────────────────────────────────────────────
To prevent memory leaks and database lockups, we implement the SQLAlchemy 
"Session-per-Request" pattern using the `get_db()` generator function.
  1. A new `SessionLocal` is created right when a REST endpoint is called.
  2. The session is `yield`ed to the endpoint to perform its CRUD.
  3. The `finally: db.close()` block ensures the connection is returned to the
     pool under ANY circumstance (even if an exception crashes the endpoint).

SCALABILITY NOTE (100M USERS)
─────────────────────────────────────────────────────────────────────────────
SQLite is sufficient for this V1 prototype, but in a Tier-1 production
environment with 100M CCU, this entire block would be refactored to point to 
a distributed, sharded cluster (like CockroachDB or Google Spanner) coupled 
with a separate leader/follower replication topology.
"""

# Use SQLite for simplicity as planned
#
# SYSTEM DESIGN NOTE (100M Users):
# -------------------------------
# In a 100M concurrent user environment, SQLite is TOTALLY INSUFFICIENT.
# Refactoring for Scale:
# 1. DISTRIBUTED SQL: Swap SQLite for a distributed relational DB like 
#    CockroachDB, Google Spanner, or a sharded PostgreSQL cluster.
# 2. READ REPLICAS: Implement a Leader/Follower pattern to handle massive 
#    read volume for session data and metadata.
# 3. VERTICAL vs HORIZONTAL: Move beyond a single node to horizontal 
#    sharding based on 'user_id' or 'org_id'.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'data', 'app.db')}"

# create_engine: 
# The Engine is the starting point for any SQLAlchemy application. It’s a 
# "home base" for the actual database connection, handling both the database 
# dialect (how to talk to SQLite) and the connection pool.
# 'check_same_thread': False is specific to SQLite to allow multi-threaded access.
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# SessionLocal:
# The sessionmaker factory generates new Session objects. Each session represents 
# a "handle" to the database. We disable autocommit/autoflush to ensure we have 
# explicit control over when data is written to the DB.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base:
# The declarative_base class is the "source of truth" for our models. 
# Any class inheriting from Base will be automatically mapped to a 
# database table and included in the metadata.
Base = declarative_base()

def get_db():
    """
    Dependency helper that provides a database session to FastAPI routes.
    
    This uses a generator pattern:
    1. Creates a local session for the specific request.
    2. 'Yields' the session to the route function.
    3. Guarantees the session is closed in the 'finally' block, 
       preventing memory leaks and connection exhaustion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
