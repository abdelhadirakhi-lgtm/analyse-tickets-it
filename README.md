# Analyse des tickets de support informatique

Application Streamlit d'analyse des tickets IT avec pandas et matplotlib. Elle reprend les six axes du notebook d'analyse : types de demandes, services, SLA par priorité, temps de première réponse par canal, évolution mensuelle et recommandations opérationnelles.

## Fichiers du projet

- `app.py` : application web Streamlit.
- `01_Technologie_IT.xlsx` : fichier de données source. La feuille `Données` doit contenir les en-têtes à la troisième ligne.
- `analyse_tickets_support.ipynb` : notebook d'analyse d'origine.
- `requirements.txt` : dépendances Python.

## Lancer localement dans VS Code

1. Ouvrir le dossier du projet dans VS Code.
2. Dans le terminal, installer les dépendances :

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Lancer l'application :

   ```bash
   python -m streamlit run app.py
   ```

4. Ouvrir l'adresse locale indiquée dans le terminal, généralement `http://localhost:8501`.

## Héberger avec Streamlit Community Cloud

1. Créer un dépôt GitHub et y ajouter `app.py`, `requirements.txt` et `01_Technologie_IT.xlsx` (ainsi que le notebook et ce README si souhaité).
2. Aller sur https://share.streamlit.io/ et connecter le compte GitHub.
3. Choisir **Create app**, le dépôt, la branche et `app.py` comme fichier principal.
4. Déployer l'application. Streamlit installe les dépendances à partir de `requirements.txt`.

## Confidentialité des données

Le dépôt et l'application peuvent rendre le fichier Excel accessible à des personnes extérieures selon les paramètres choisis. Avant de publier le projet, vérifier que le classeur ne contient pas de données personnelles, confidentielles ou internes. Si c'est le cas, utiliser un jeu de données anonymisé ou une méthode de stockage privé adaptée.

## Notes sur les calculs

- Le fichier est lu avec `header=2` depuis la feuille `Données`.
- Un dépassement SLA est défini comme `Résolution (h) > Objectif SLA (h)`.
- Les tickets non résolus ou sans délai/objectif renseigné sont exclus du dénominateur des taux SLA.
- Les filtres de la barre latérale s'appliquent à l'ensemble du tableau de bord.
