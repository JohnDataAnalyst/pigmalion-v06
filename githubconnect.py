# automate_git.py
import os
import subprocess
import sys
import shutil

def run(cmd, check=True):
    """
    Lance une commande shell (list de strings), affiche stdout/stderr,
    et retourne le code retour. Si check=True, lève une exception en cas d'erreur.
    """
    print(f">>> {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, cmd)
    return result.returncode

def ensure_models_ignored(gitignore_path: str):
    """
    Vérifie que 'models/' figure dans .gitignore ; sinon, l'ajoute.
    """
    if not os.path.isfile(gitignore_path):
        print(f"[INFO] Création de {gitignore_path}.")
        with open(gitignore_path, "w", encoding="utf-8") as f:
            f.write("models/\n")
        return True

    with open(gitignore_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    if "models/" in (line.strip() for line in lines):
        print("[INFO] 'models/' est déjà présent dans .gitignore.")
        return False

    print("[INFO] Ajout de 'models/' dans .gitignore.")
    with open(gitignore_path, "a", encoding="utf-8") as f:
        # On ajoute une ligne vide si besoin, puis 'models/'
        if lines and lines[-1].strip() != "":
            f.write("\n")
        f.write("models/\n")
    return True

def main():
    # 1) Vérifier qu'on est bien à la racine du projet Git
    if not os.path.isdir(".git"):
        print("Erreur : ce script doit être lancé depuis la racine d'un dépôt Git.")
        sys.exit(1)

    # 2) Mettre à jour .gitignore pour ignorer models/
    gitignore_path = os.path.join(os.getcwd(), ".gitignore")
    ignore_changed = ensure_models_ignored(gitignore_path)

    # 3) Si models/ était précédemment suivi, le retirer de l'index
    #    'git ls-files --error-unmatch models/' renverra 0 si models/ est suivi, erreur sinon
    models_path = os.path.join(os.getcwd(), "models")
    if os.path.isdir(models_path):
        try:
            run(["git", "ls-files", "--error-unmatch", "models/"], check=True)
            print("[INFO] models/ était suivi par Git -> suppression de l'index (cached).")
            run(["git", "rm", "-r", "--cached", "models/"])
        except subprocess.CalledProcessError:
            print("[INFO] models/ n'était pas suivi par Git. Rien à faire.")
    else:
        print("[INFO] Aucun dossier 'models/' trouvé, on ignore cette étape.")

    # 4) Stager le .gitignore si on l'a modifié
    if ignore_changed:
        run(["git", "add", ".gitignore"])

    # 5) Ajouter tous les autres fichiers (non-ignorés)
    run(["git", "add", "."])

    # 6) Vérifier s'il y a quelque chose à committer
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout.strip()
    if not status:
        print("[INFO] Rien à committer. L'arbre de travail est propre.")
    else:
        # 7) Créer un commit
        commit_message = "Initial commit : ajout backend, frontend, scripts de lancement et mise à jour .gitignore"
        run(["git", "commit", "-m", commit_message])

    # 8) Vérifier si la branche main existe localement
    branches = subprocess.run(["git", "branch"], capture_output=True, text=True).stdout
    if "main" not in branches:
        print("[INFO] Renommage de la branche courante en 'main'.")
        run(["git", "branch", "-M", "main"])

    # 9) Vérifier ou ajouter le remote 'origin'
    remotes = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True).stdout
    if "origin" not in remotes:
        print("[ERREUR] Aucun remote 'origin' trouvé. Veuillez d'abord : git remote add origin <URL_DU_DEPOT>.")
        sys.exit(1)

    # 10) Pousser sur origin/main
    #     --set-upstream sert à lier la branche locale à origin/main si c'est la première fois
    print("[INFO] Poussée vers github : origin/main.")
    try:
        run(["git", "push", "-u", "origin", "main"])
    except subprocess.CalledProcessError:
        print("[ERREUR] Échec du 'git push'. Vérifiez votre accès au dépôt distant.")
        sys.exit(1)

    print("\n==> Opération terminée : votre projet a été poussé sur GitHub.") 

if __name__ == "__main__":
    main()
