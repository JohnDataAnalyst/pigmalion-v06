# 01_ANALYSE_POST_UNITAIRE.py
# -*- coding: utf-8 -*-
"""
Analyse en boucle de posts Bluesky (unitaire)
────────────────────────────────────────────────────────────────────────────
Entrez successivement les URLs de posts à analyser. Tapez « q » (ou Entrée
sur une ligne vide) pour quitter.
────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import os
import re
import sys
import shutil
import textwrap
from pathlib import Path
from datetime import datetime, timezone
from atproto import Client
from dotenv import load_dotenv
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
    pipeline
)

# ╭────────────────── 1. Auth Bluesky ──────────────────╮
# Construire le chemin vers backend/.env10 à partir de ce fichier
BASE_DIR = Path(__file__).parent.parent  # remonte de 'analyse/' vers 'backend/'
ENV_PATH = BASE_DIR / ".env10"
load_dotenv(dotenv_path=str(ENV_PATH))

HANDLE, PASSWORD = os.getenv("BLUESKY_HANDLE"), os.getenv("BLUESKY_PASSWORD")
if not HANDLE or not PASSWORD:
    sys.exit("BLUESKY_HANDLE / BLUESKY_PASSWORD manquants")

client = Client()
client.login(HANDLE, PASSWORD)

# ╭────────────────── 2. Modèles locaux ────────────────╮
from pathlib import Path
import torch

# 2.1. Construire la racine du projet (jusqu’à 06_PIGMALION_V06/)
PROJECT_ROOT = Path(__file__).parent.parent.parent
#    - __file__ est ".../backend/analyse/01_ANALYSE_POST_UNITAIRE.py"
#    - Path(__file__).parent       => ".../backend/analyse/"
#    - Path(__file__).parent.parent => ".../backend/"
#    - Path(__file__).parent.parent.parent => ".../06_PIGMALION_V06/"

# 2.2. On définit le dossier "models" à la racine du projet
MODELS_DIR = PROJECT_ROOT / "models"
# Vos sous-dossiers de modèles doivent être exactement :
#    06_PIGMALION_V06/models/cardiffnlp_tweet-topic-21-multi/
#    06_PIGMALION_V06/models/cardiffnlp_twitter-roberta-base-irony/
#    06_PIGMALION_V06/models/finiteautomata_bertweet-base-sentiment-analysis/
#    06_PIGMALION_V06/models/ghanashyamvtatti_roberta-fake-news/
#    06_PIGMALION_V06/models/j-hartmann_emotion-english-distilroberta-base/
#    06_PIGMALION_V06/models/unitary_toxic-bert/

# 2.3. Construire les chemins complets vers chacun des modèles
TOPIC_PATH   = MODELS_DIR / "cardiffnlp_tweet-topic-21-multi"
IRONY_PATH   = MODELS_DIR / "cardiffnlp_twitter-roberta-base-irony"
SENTI_PATH   = MODELS_DIR / "finiteautomata_bertweet-base-sentiment-analysis"
FAKENEWS_PATH= MODELS_DIR / "ghanashyamvtatti_roberta-fake-news"
EMO_PATH     = MODELS_DIR / "j-hartmann_emotion-english-distilroberta-base"
TOX_PATH     = MODELS_DIR / "unitary_toxic-bert"

# 2.4. Détecter si on a un GPU disponible (pour le pipeline Hugging Face)
device_id = 0 if torch.cuda.is_available() else -1

def load_pipe(path: Path, fn: str):
    """
    Charge un pipeline Hugging Face en local depuis le dossier 'path'.
    - path : objet Path pointant vers un dossier contenant config.json + pytorch_model.bin (ou équivalent)
    - fn   : nom de la fonction d'activation ('sigmoid', 'softmax', etc.)
    """
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Dossier de modèle introuvable : {path}")

    return pipeline(
        "text-classification",
        model     = AutoModelForSequenceClassification.from_pretrained(str(path), local_files_only=True),
        tokenizer = AutoTokenizer.from_pretrained(str(path), local_files_only=True),
        top_k     = None,
        function_to_apply = fn,
        device    = device_id
    )

print("⌛  Chargement des modèles …")
pipe_topic    = load_pipe(TOPIC_PATH,    "softmax")  # ex. topic classification
pipe_irony    = load_pipe(IRONY_PATH,    "softmax")  # ex. irony detection
pipe_senti    = load_pipe(SENTI_PATH,    "softmax")  # ex. sentiment analysis
pipe_fakenews = load_pipe(FAKENEWS_PATH, "softmax")  # ex. fake-news detection
pipe_emo      = load_pipe(EMO_PATH,      "softmax")  # ex. emotion classification
pipe_tox      = load_pipe(TOX_PATH,      "sigmoid")  # ex. toxicité
print("✅  Modèles prêts.\n")
# ╰─────────────────────────────────────────────────────╯


# ╭────────────────── 3. Fonctions utilitaires ─────────╮
POND = {
    "bio vide": .2,
    "aucun site": .1,
    "fréq élevée": .2,
    "peu followers": .2,
    "diff nom/handle": .2,
    "non vérifié": .1
}
MOTIFS_TXT = {
    "bio vide": "biographie vide",
    "aucun site": "pas de site web",
    "fréq élevée": "fréquence de publication très élevée",
    "peu followers": "très peu de followers",
    "diff nom/handle": "nom différent du handle",
    "non vérifié": "pas de badge vérifié"
}
EMO_FR = {
    "anger": "colère",
    "disgust": "dégoût",
    "fear": "peur",
    "joy": "joie",
    "sadness": "tristesse",
    "surprise": "surprise"
}

def wrap(txt: str, width: int) -> str:
    return textwrap.fill(txt, width=width, subsequent_indent=" " * 36)

def nettoyer(txt: str) -> str:
    txt = re.sub(r"http\S+|[@#]\S+|[^\w\s’']", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()

def liste_fr(lst: list[str]) -> str:
    return lst[0] if len(lst) == 1 else ", ".join(lst[:-1]) + " et " + lst[-1]
# ╰─────────────────────────────────────────────────────╯

# ╭────────────────── 4. Analyse d’une URL ─────────────╮
def analyser_post(url: str) -> dict:
    """
    Analyse un post Bluesky à partir de son URL.
    Renvoie un dictionnaire contenant toutes les informations.
    """
    # Vérification du format d’URL
    m = re.fullmatch(r"https?://bsky\.app/profile/([^/]+)/post/([^/?#]+)", url)
    if not m:
        return {"error": "URL Bluesky invalide."}
    handle_in_url, rkey = m.groups()
    try:
        did = client.com.atproto.identity.resolve_handle({"handle": handle_in_url}).did
    except Exception:
        return {"error": "Impossible de résoudre le DID pour ce handle."}
    uri = f"at://{did}/app.bsky.feed.post/{rkey}"

    # Récupération du post et du profil
    try:
        post = client.app.bsky.feed.get_posts({"uris": [uri]}).posts[0]
    except Exception:
        return {"error": "Post introuvable ou supprimé."}
    profile = client.app.bsky.actor.get_profile({"actor": did})

    # ─── Méta-données ────────────────────────────────────────────────
    text_raw = re.sub(r"\n{2,}", "\n", (post.record.text or "").replace("\r", "").strip())
    reply_cnt  = int(post.reply_count  or 0)
    repost_cnt = int(post.repost_count or 0)
    like_cnt   = int(post.like_count   or 0)

    name       = profile.display_name or handle_in_url
    created_dt = datetime.fromisoformat(profile.created_at.rstrip("Z")).replace(tzinfo=timezone.utc)
    following  = int(profile.follows_count   or 0)
    followers  = int(profile.followers_count or 0)

    total_posts = int(getattr(profile, "posts_count", 0))
    days_live   = max((datetime.now(timezone.utc) - created_dt).days, 1)
    posts_per_d = round(total_posts / days_live, 3)

    ratio_follow = round((followers / following) if following else 0, 3)
    bio_vide    = not bool(profile.description and profile.description.strip())
    site_web    = bool(re.search(r"https?://|bsky://", profile.description or ""))
    badge_ok    = any(getattr(l, "val", "") == "verified" for l in (getattr(profile, "labels", []) or []))

    # ─── Toxicité & émotions ─────────────────────────────────────────
    tox_lbl = ["toxic", "obscene", "insult", "severe_toxic", "identity_hate", "threat"]
    emo_lbl = ["anger", "disgust", "fear", "joy", "sadness", "surprise"]
    tox_dict = {k: 0.0 for k in tox_lbl}
    emo_dict = {k: 0.0 for k in emo_lbl}

    if text_raw:
        # Analyse toxicité
        for p in pipe_tox(nettoyer(text_raw))[0]:
            tox_dict[p["label"].lower()] = round(float(p["score"]), 3)
        # Analyse émotions
        for p in pipe_emo(nettoyer(text_raw))[0]:
            l = p["label"].lower()
            if l in emo_dict:
                emo_dict[l] = round(float(p["score"]), 3)

    # ─── Score bot (surface) ─────────────────────────────────────────
    motifs = []
    if bio_vide:
        motifs.append("bio vide")
    if not site_web:
        motifs.append("aucun site")
    if posts_per_d > 20:
        motifs.append("fréq élevée")
    if followers < 10:
        motifs.append("peu followers")
    if name and abs(len(name) - len(handle_in_url)) > 5:
        motifs.append("diff nom/handle")
    if not badge_ok:
        motifs.append("non vérifié")

    score_bot = sum(POND[m] for m in motifs)
    analyse_compl = "Non"

    label_bot = (
        "Probable bot" if score_bot >= .6 else
        "Suspicion"    if score_bot >= .4 else
        "Probable humain"
    )

    if label_bot == "Probable humain":
        comment_bot = "Au vu des signaux observés, le profil semble géré par une personne réelle."
    elif label_bot == "Probable bot":
        comment_bot = (
            "Tout indique un compte automatisé : "
            + liste_fr([MOTIFS_TXT[m] for m in motifs]) + "."
        )
    else:  # Suspicion
        comment_bot = (
            "Certains signaux invitent à la prudence : "
            + liste_fr([MOTIFS_TXT[m] for m in motifs]) + "."
        )

    # ─── Tonalité ───────────────────────────────────────────────────
    main_emo = max(emo_dict, key=emo_dict.get)
    main_pct = int(round(emo_dict[main_emo] * 100))
    tox_val = max(tox_dict.values())
    tox_desc = (
        "non toxique"           if tox_val < .01 else
        "légèrement toxique"    if tox_val < .20 else
        "modérément toxique"    if tox_val < .50 else
        "fortement toxique"
    )
    comment_tone = (
        f"Le post est {tox_desc} et exprime principalement "
        f"de la {EMO_FR[main_emo]} ({main_pct} %)."
    )

    # ─── Préparation des champs de sortie ─────────────────────────────────
    rows = [
        ("in_post_saisie_url", url),
        ("out_post_text", wrap(text_raw, width=shutil.get_terminal_size((110, 24)).columns - 37)),
        ("out_post_comment", reply_cnt),
        ("out_post_repost", repost_cnt),
        ("out_post_like", like_cnt),
        ("out_compte_name", name),
        ("out_compte_creationdate", f"{created_dt:%Y-%m-%d}"),
        ("out_compte_following", following),
        ("out_compte_followers", followers),
        ("Analyse_compte_ratio_following_followers", ratio_follow),
        ("Analyse_compte_nombre_total_posts", total_posts),
        ("Analyse_compte_moyenne_quotidienne_posts", posts_per_d),
        ("Analyse_compte_bio_vide", "oui" if bio_vide else "non"),
        ("Analyse_compte_site_web", "oui" if site_web else "non"),
        ("Analyse_compte_badge_verifie", "oui" if badge_ok else "non"),
        ("out_post_score_toxicite_toxic", tox_dict["toxic"]),
        ("out_post_score_toxicite_obscene", tox_dict["obscene"]),
        ("out_post_score_toxicite_insult", tox_dict["insult"]),
        ("out_post_score_toxicite_toxicsevere", tox_dict["severe_toxic"]),
        ("out_post_score_toxicite_hate", tox_dict["identity_hate"]),
        ("out_post_score_toxicite_threat", tox_dict["threat"]),
        ("out_post_score_sentiments_anger", emo_dict["anger"]),
        ("out_post_score_sentiments_disgust", emo_dict["disgust"]),
        ("out_post_score_sentiments_fear", emo_dict["fear"]),
        ("out_post_score_sentiments_joy", emo_dict["joy"]),
        ("out_post_score_sentiments_sadness", emo_dict["sadness"]),
        ("out_post_score_sentiments_surprise", emo_dict["surprise"]),
        ("out_post_score_botdetection", round(score_bot, 3)),
        ("out_post_text_analyse_contenu", comment_bot),
        ("out_post_commentaire_tonalite", comment_tone),
        ("out_post_compte_analyse_complementaire", analyse_compl),
    ]

    # ─── On transforme "rows" en dictionnaire JSON-able ───────────────────────
    output_dict = {}
    for label, val in rows:
        cle = label.replace("/", "_")
        output_dict[cle] = val

    # ─── On renvoie le dictionnaire (pour que FastAPI l’utilise) ──────────────
    return output_dict


# ╭────────────────── 5. Boucle interactive (standalone) ───────────╮
if __name__ == "__main__":
    while True:
        try:
            url = input("📝  URL du post (ou q pour quitter) : ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋  Fin de session.")
            break
        if not url or url.lower() in {"q", "quit", "exit"}:
            print("👋  Fin de session.")
            break

        result = analyser_post(url)
        if "error" in result:
            print(f"⛔  {result['error']}\n")
            continue

        print("\n───────────── Résultat ─────────────")
        for key, val in result.items():
            if isinstance(val, float):
                print(f"{key:<37}: {val:.3f}" if not val.is_integer() else f"{key:<37}: {int(val)}")
            else:
                print(f"{key:<37}: {val}")
        print()
