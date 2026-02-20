import os
import pymysql
from dotenv import load_dotenv

load_dotenv()


def get_conn():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "ai_docs"),
        port=int(os.getenv("DB_PORT", "3306")),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


# =========================
# 1) FILES
# =========================
def insert_file(original_name: str, mime_type: str, input_path: str) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO files (original_name, mime_type, input_path, status)
                VALUES (%s,%s,%s,'UPLOADED')
                """,
                (original_name, mime_type, input_path),
            )
            return cur.lastrowid


def get_file(file_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM files WHERE id=%s", (file_id,))
            return cur.fetchone()


def list_files(limit: int = 50):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM files ORDER BY id DESC LIMIT %s", (limit,))
            return cur.fetchall()


def set_status(file_id: int, status: str, error_message=None, output_path=None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE files
                SET status=%s,
                    error_message=%s,
                    output_path=COALESCE(%s, output_path)
                WHERE id=%s
                """,
                (status, error_message, output_path, file_id),
            )


# =========================
# 2) PROJECTS
# =========================
def list_projects(limit: int = 200):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM projects ORDER BY id DESC LIMIT %s", (limit,))
            return cur.fetchall()


def get_project(project_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM projects WHERE id=%s", (project_id,))
            return cur.fetchone()

def get_project_by_title(title: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM projects WHERE title=%s LIMIT 1", (title,))
            return cur.fetchone()


def insert_project(data: dict) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO projects
                (title, domain, primary_entity, constraints_text, advanced_feature,
                 security_access, reporting_requirement, common_tasks)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    data["title"],
                    data["domain"],
                    data["primary_entity"],
                    data.get("constraints_text", ""),
                    data.get("advanced_feature", ""),
                    data.get("security_access", ""),
                    data.get("reporting_requirement", ""),
                    data.get("common_tasks", ""),
                ),
            )
            return cur.lastrowid



# =========================
# 3) PROJECT AI OUTPUTS
# =========================
def insert_project_output(
    project_id: int,
    action_key: str,
    prompt_text: str,
    output_text: str,
    model: str,
    temperature: float = 0.2,
) -> int:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO project_ai_outputs
                (project_id, action_key, prompt_text, output_text, model, temperature)
                VALUES (%s,%s,%s,%s,%s,%s)
                """,
                (project_id, action_key, prompt_text, output_text, model, temperature),
            )
            return cur.lastrowid


def get_latest_project_output(project_id: int, action_key: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM project_ai_outputs
                WHERE project_id=%s AND action_key=%s
                ORDER BY id DESC
                LIMIT 1
                """,
                (project_id, action_key),
            )
            return cur.fetchone()


def list_project_outputs(project_id: int, limit: int = 50):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT *
                FROM project_ai_outputs
                WHERE project_id=%s
                ORDER BY id DESC
                LIMIT %s
                """,
                (project_id, limit),
            )
            return cur.fetchall()

