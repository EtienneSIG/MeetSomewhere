# MeetSomewhere

Une application Streamlit pour déterminer le point de rencontre idéal entre plusieurs adresses, en tenant compte de différents modes de transport et de contraintes personnalisables de distance/temps.


## Application in streamlit cloud

https://meetsomewhere-2td6i3kpnvu3cafawqsgad.streamlit.app/

## Fonctionnalités

- Saisie de plusieurs adresses (jusqu'à 10)
- Choix du mode de transport :
  - Voiture
  - Voiture électrique
  - Vélo (standard, route, montagne, électrique)
  - À pied
  - Fauteuil roulant
- Contraintes personnalisables :
  - Temps maximal de trajet
  - Distance maximale
- Visualisation sur carte avec :
  - Marqueurs pour chaque adresse
  - Point de rencontre optimal
  - Itinéraires vers le point de rencontre
- Tableau détaillé des temps de trajet et distances pour chaque adresse

## Installation

1. Cloner le dépôt :
```
git clone <url-du-repo>
cd MeetSomewhere
```

2. Installer les dépendances :
```
pip install -r requirements.txt
```

3. Créer un fichier `.env` avec votre clé API OpenRoute Service :
```
OPENROUTE_API_KEY=votre_clé_api_ici
```

Pour obtenir une clé API OpenRoute Service, inscrivez-vous sur [https://openrouteservice.org/](https://openrouteservice.org/).

## Utilisation

1. Lancer l'application :
```
streamlit run app.py
```

2. Accéder à l'application dans votre navigateur à l'adresse indiquée (généralement http://localhost:8501)

3. Renseigner les adresses et les paramètres dans l'interface

4. Cliquer sur "Find Meeting Point" pour calculer et afficher le point de rencontre idéal

## Note sur l'API

Cette application utilise l'API gratuite d'OpenRoute Service qui a des limites d'utilisation. Pour une utilisation intensive, envisagez de passer à un plan payant.

## Dépendances principales

- Streamlit - Interface utilisateur
- Folium - Visualisation de cartes
- OpenRoute Service API - Calcul d'itinéraires et de temps de trajet
- GeoPy - Géocodage d'adresses
