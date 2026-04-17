import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("db_repair")

# Locate the database
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "app.db")

def repair():
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found at {DB_PATH}. Nothing to repair.")
        return

    logger.info(f"Connecting to database at {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # List of columns to add to 'messages' table
    # format: (name, type)
    new_columns = [
        ("total_latency_ms", "INTEGER"),
        ("retrieval_latency_ms", "INTEGER"),
        ("generation_latency_ms", "INTEGER"),
        ("prompt_tokens", "INTEGER"),
        ("completion_tokens", "INTEGER"),
        ("faithfulness", "FLOAT"),
        ("answer_relevancy", "FLOAT"),
        ("context_precision", "FLOAT"),
        ("context_recall", "FLOAT")
    ]

    # Get existing columns
    cursor.execute("PRAGMA table_info(messages)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    added_count = 0
    for col_name, col_type in new_columns:
        if col_name not in existing_columns:
            try:
                logger.info(f"Adding column '{col_name}' ({col_type}) to 'messages' table...")
                cursor.execute(f"ALTER TABLE messages ADD COLUMN {col_name} {col_type}")
                added_count += 1
            except Exception as e:
                logger.error(f"Failed to add column {col_name}: {e}")
        else:
            logger.info(f"Column '{col_name}' already exists.")

    conn.commit()
    conn.close()
    
    if added_count > 0:
        logger.info(f"Repair complete. Added {added_count} missing columns.")
    else:
        logger.info("No repair needed. All columns are present.")

if __name__ == "__main__":
    repair()
