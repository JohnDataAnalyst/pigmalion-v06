import subprocess
import os
from datetime import datetime

def run(cmd):
    """Exécute une commande shell et retourne sa sortie."""
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True)
    return result.stdout.strip(), result.stderr.strip()

def list_tags():
    stdout, _ = run("git tag --sort=creatordate")
    return stdout.splitlines()

def save_mode():
    print("\n💾 Sauvegarde du projet Git\n")
    description = input("📝 Entrez une description courte : ").strip().lower()
    description = description.replace(" ", "_").replace("é", "e").replace("è", "e").replace("à", "a").replace("ç", "c")
    timestamp = datetime.now().strftime("%Y_%m_%d_%Hh%M")
    tag_name = f"sauvegarde_{timestamp}_{description}"

    run("git add .")
    run(f"git commit -m \"💾 Sauvegarde automatique : {description}\"")
    run(f"git tag {tag_name}")
    run("git push")
    run(f"git push origin {tag_name}")

    print(f"\n✅ Sauvegarde terminée avec le tag : {tag_name}\n")

def load_mode():
    print("\n📦 Chargement d'une sauvegarde\n")
    tags = list_tags()
    if not tags:
        print("Aucune sauvegarde disponible.")
        return

    for i, tag in enumerate(tags, start=1):
        print(f"{i:2d} - {tag}")

    choice = input("\n👉 Entrez le numéro de la sauvegarde à charger : ")
    try:
        index = int(choice) - 1
        if 0 <= index < len(tags):
            tag_to_load = tags[index]
            print(f"\n🔄 Restauration du tag : {tag_to_load}\n")
            run("git stash push -m 'backup avant restauration'")
            run(f"git checkout {tag_to_load}")  # détaché
            print("✅ Restauration terminée. Vous êtes en mode détaché.")
            print("ℹ️ Tapez `git checkout main` pour revenir à la branche principale.")
        else:
            print("❌ Numéro invalide.")
    except ValueError:
        print("❌ Entrée non valide.")

def main():
    os.chdir(os.path.dirname(__file__))  # exécuter à la racine du projet
    mode = input("🔧 Que voulez-vous faire ? [s = save / l = load] : ").strip().lower()
    if mode == "s":
        save_mode()
    elif mode == "l":
        load_mode()
    else:
        print("❌ Mode invalide. Tapez 's' ou 'l'.")

if __name__ == "__main__":
    main()
