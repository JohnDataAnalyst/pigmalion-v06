import psycopg2
import os
from datetime import date, timedelta
from dotenv import load_dotenv

# Chargement des variables d'environnement
load_dotenv(".env10")

# Connexion PostgreSQL
conn = psycopg2.connect(
    dbname=os.getenv("DB_NAME"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    host=os.getenv("DB_HOST"),
    port=os.getenv("DB_PORT")
)

# Définir la période des 7 derniers jours
end_date = date.today() - timedelta(days=1)
start_date = end_date - timedelta(days=6)

# Liste des colonnes numériques à agréger
columns = [
    'post_occurrence', 'mean_anger', 'mean_disgust', 'mean_fear',
    'mean_joy', 'mean_surprise', 'mean_toxic', 'mean_severe_toxic',
    'mean_obscene', 'mean_threat', 'mean_insult', 'mean_hate'
]

def get_averages(cur, date_clause: str, label: str):
    query = f"""
        SELECT 
            AVG(post_occurrence)::float,
            {', '.join([f'AVG({col})::float' for col in columns[1:]])}
        FROM trends_results
        WHERE categorie = 'news_social_concern' {date_clause};
    """
    cur.execute(query)
    result = cur.fetchone()
    print(f"\n{label}")
    print("-" * len(label))
    if result and any(result):
        for col, val in zip(['avg_' + c for c in columns], result):
            # post_occurrence laissé tel quel, le reste x100
            if col == 'avg_post_occurrence':
                print(f"{col}: {val:.2f}")
            else:
                print(f"{col}: {val * 100:.2f} %")
    else:
        print("Aucune donnée disponible.")

# Exécution
with conn.cursor() as cur:
    get_averages(cur, f"AND post_date BETWEEN '{start_date}' AND '{end_date}'", "MOYENNE SUR LES 7 DERNIERS JOURS")
    get_averages(cur, "", "MOYENNE GLOBALE (TOUS TEMPS)")

conn.close()
