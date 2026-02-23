import os
import psycopg
from dotenv import load_dotenv

class Database:
    
    def __init__(self):
        self.db_host = os.environ.get("DB_HOST")
        self.db_port = os.environ.get("DB_PORT", "5432") # Puxa a porta 5432 como fallback se não achar
        self.db_name = os.environ.get("DB_NAME")
        self.db_user = os.environ.get("DB_USER")
        self.db_pass = os.environ.get("DB_PASSWORD")

        database_vars = [self.db_host, self.db_name, self.db_user, self.db_pass]
        if not all(database_vars):
            raise ValueError("ERROR: missing database configuration variables in .env file.")

    def connect(self):
        conn_info = f"host={self.db_host} port={self.db_port} dbname={self.db_name} user={self.db_user} password={self.db_pass}"
        return psycopg.connect(conn_info)

    def get_question_structure(self, integration_id):
        try:
            with self.connect() as conn:
                with conn.cursor() as cur:

                    cur.execute("SELECT id, statement FROM question WHERE integration_id = %s;", (integration_id,))

                    print(f"Fetched {cur.results} questions for integration_id {integration_id}.")
                    return cur.fetchall()
                

        except Exception as e:
            print(f"Database error: {e}")
            return []
