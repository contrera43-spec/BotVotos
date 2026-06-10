import sqlite3
import psycopg2

SQLITE_DB = "votos.db"

POSTGRES_URL = "postgresql://botvotos_db_user:VIW4qn5pSg8mPq16UVna5AWt16rJmRH1@dpg-d8kp1ii8qa3s738aark0-a.oregon-postgres.render.com/botvotos_db"

print("Abriendo SQLite...")
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_cursor = sqlite_conn.cursor()

print("Conectando a PostgreSQL...")
pg_conn = psycopg2.connect(
    POSTGRES_URL,
    sslmode="require"
)
pg_cursor = pg_conn.cursor()

print("Creando tabla...")
pg_cursor.execute("""
CREATE TABLE IF NOT EXISTS votos (
    mensaje_id BIGINT PRIMARY KEY,
    usuario TEXT,
    fecha TEXT
)
""")
pg_conn.commit()

print("Leyendo SQLite...")
sqlite_cursor.execute("""
SELECT mensaje_id, usuario, fecha
FROM votos
""")

votos = sqlite_cursor.fetchall()

print(f"Votos encontrados: {len(votos)}")

print("Migrando todos los votos...")

contador = 0

for voto in votos:

    pg_cursor.execute(
        """
        INSERT INTO votos
        (mensaje_id, usuario, fecha)
        VALUES (%s, %s, %s)
        ON CONFLICT (mensaje_id) DO NOTHING
        """,
        voto
    )

    contador += 1

    if contador % 100 == 0:
        print(f"Migrados {contador}")

pg_conn.commit()

print(f"✅ Migrados {contador} votos")

sqlite_conn.close()
pg_conn.close()

print("Fin")