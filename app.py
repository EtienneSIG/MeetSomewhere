import streamlit as st
import folium
from folium.plugins import HeatMap
import requests
import polyline
import numpy as np
import pandas as pd
from streamlit_folium import folium_static
from geopy.geocoders import Nominatim
import time
import math
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variables or set a placeholder
OPENROUTE_API_KEY = os.getenv("OPENROUTE_API_KEY", "")

# Page configuration
st.set_page_config(
    page_title="MeetSomewhere - Find the Ideal Meeting Point",
    page_icon="🗺️",
    layout="wide"
)

# Styles CSS pour rendre la carte responsive
st.markdown("""
<style>
    .stApp {
        max-width: 100%;
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .css-1v3fvcr {
        max-width: 100%;
    }
    .folium-map {
        width: 100%;
        height: 70vh;
    }
    .dataframe {
        width: 100% !important;
    }
    .css-1ekf893 {
        width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)

# App title and description
st.title("MeetSomewhere 🗺️")

# Sidebar configuration
with st.sidebar:
    st.header("Settings")
    
    # API Key input
    if not OPENROUTE_API_KEY:
        OPENROUTE_API_KEY = st.text_input("OpenRoute Service API Key", 
                                         help="Get your API key from https://openrouteservice.org/")
        if not OPENROUTE_API_KEY:
            st.warning("Please enter your OpenRoute Service API key to use this application")
    
    # Transportation mode
    transport_mode = st.selectbox(
        "Transportation Mode",
        [
            "driving-car", 
            "driving-hgv", 
            "cycling-regular", 
            "cycling-road", 
            "cycling-mountain", 
            "cycling-electric", 
            "foot-walking", 
            "foot-hiking", 
            "wheelchair"
        ],
        index=0
    )
    
    # Maximum travel time/distance
    constraint_type = st.radio("Constraint Type", ["Time", "Distance"])
    
    if constraint_type == "Time":
        max_constraint = st.slider("Maximum travel time (minutes)", 5, 300, 60, 5)
    else:
        max_constraint = st.slider("Maximum travel distance (km)", 1, 1000, 30, 5)
    
    # Number of addresses
    num_addresses = st.number_input("Number of addresses", 2, 10, 3, 1)

# Main content
address_inputs = []
st.subheader("Enter Addresses")

# Create address input fields
for i in range(int(num_addresses)):
    address_inputs.append(st.text_input(f"Address {i+1}", key=f"address_{i}"))

# Initialize geocoder
geolocator = Nominatim(user_agent="meetsomewhere-app")

# Function to geocode an address
def geocode_address(address):
    try:
        location = geolocator.geocode(address)
        if location:
            return location.latitude, location.longitude
        else:
            st.error(f"Could not geocode address: {address}")
            return None
    except Exception as e:
        st.error(f"Error geocoding address {address}: {str(e)}")
        return None

# Function to get route between two points
def get_route(start_coords, end_coords, profile="driving-car"):
    # Selon la documentation OpenRoute Service API v2
    url = f"https://api.openrouteservice.org/v2/directions/{profile}/geojson"
    
    # L'API key doit être dans l'en-tête comme suit
    headers = {
        'Accept': 'application/json, application/geo+json',
        'Authorization': f"{OPENROUTE_API_KEY}",
        'Content-Type': 'application/json'
    }
    
    # Format de données attendu par l'API : [[lon1, lat1], [lon2, lat2]]
    data = {
        "coordinates": [
            [start_coords[1], start_coords[0]],  # [lon, lat]
            [end_coords[1], end_coords[0]]       # [lon, lat]
        ]
    }
    
    try:
        # Requête API sans affichage de débogage
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 429:
            # Erreur silencieuse - ne pas afficher à l'utilisateur
            raise Exception("API_RATE_LIMIT_EXCEEDED")
        elif response.status_code == 404:
            # Erreur silencieuse - ne pas afficher à l'utilisateur
            raise Exception("ROUTE_NOT_FOUND")
        elif response.status_code != 200:
            # Erreur silencieuse - ne pas afficher à l'utilisateur
            raise Exception(f"API_ERROR_{response.status_code}")
            
        return response.json()
    except requests.exceptions.RequestException as e:
        # Erreur silencieuse - ne pas afficher à l'utilisateur
        raise Exception("CONNECTION_ERROR")
    except Exception as e:
        # Propager les erreurs
        raise e

# Function to get time and distance from GeoJSON route
def extract_route_info(route_data):
    try:
        if route_data and 'features' in route_data and len(route_data['features']) > 0:
            properties = route_data['features'][0]['properties']
            
            # Extract time (in seconds) and distance (in meters)
            time_seconds = properties['summary']['duration']
            distance_meters = properties['summary']['distance']
            
            # Convert to minutes and kilometers
            time_minutes = time_seconds / 60
            distance_km = distance_meters / 1000
            
            return time_minutes, distance_km
    except Exception:
        # Erreur silencieuse - ne pas afficher à l'utilisateur
        pass
    
    return None, None

# Function to calculate the ideal meeting point
def find_ideal_meeting_point(coords, profile, constraint_type, max_constraint):
    # Create a grid of potential meeting points
    # This is a simple approach - for production, you might want a more sophisticated algorithm
    lat_min = min(coord[0] for coord in coords)
    lat_max = max(coord[0] for coord in coords)
    lon_min = min(coord[1] for coord in coords)
    lon_max = max(coord[1] for coord in coords)
    
    # Calculer le centre géographique comme point de départ
    center_lat = sum(coord[0] for coord in coords) / len(coords)
    center_lon = sum(coord[1] for coord in coords) / len(coords)
    
    # Pour des adresses très distantes, on peut privilégier une recherche centrée
    # au lieu d'élargir la zone qui deviendrait trop grande
    use_centered_search = False
    
    # Calculer la distance maximale entre les points
    max_lat_distance = lat_max - lat_min
    max_lon_distance = lon_max - lon_min
    
    # Si la distance est très grande, utiliser une approche centrée
    if max_lat_distance > 3 or max_lon_distance > 3:  # Environ 300km
        use_centered_search = True
    
    if use_centered_search:
        # Créer une grille centrée autour du centre géographique
        grid_radius = min(max_lat_distance, max_lon_distance) * 0.3  # Réduire la zone de recherche
        lat_min = center_lat - grid_radius
        lat_max = center_lat + grid_radius
        lon_min = center_lon - grid_radius
        lon_max = center_lon + grid_radius
    else:
        # Expand the search area a bit
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        lat_min -= lat_range * 0.1
        lat_max += lat_range * 0.1
        lon_min -= lon_range * 0.1
        lon_max += lon_range * 0.1
    
    # Create grid
    grid_size = 10
    lat_steps = np.linspace(lat_min, lat_max, grid_size)
    lon_steps = np.linspace(lon_min, lon_max, grid_size)
    
    # Store points and their scores
    potential_points = []
    
    # Compte le nombre total de points essayés et validés
    attempted_points = 0
    successful_points = 0
    
    with st.spinner("Calculating ideal meeting point..."):
        progress_bar = st.progress(0)
        total_points = grid_size * grid_size
        counter = 0
        
        for lat in lat_steps:
            for lon in lon_steps:
                counter += 1
                progress_bar.progress(counter / total_points)
                
                point = (lat, lon)
                times = []
                distances = []
                valid_point = True
                
                # Check routes from each starting point to this potential meeting point
                for coord in coords:
                    try:
                        attempted_points += 1
                        route_data = get_route(coord, point, profile)
                        time_minutes, distance_km = extract_route_info(route_data)
                        
                        if time_minutes is not None and distance_km is not None:
                            times.append(time_minutes)
                            distances.append(distance_km)
                            
                            # Check if this point satisfies the constraint
                            if constraint_type == "Time" and time_minutes > max_constraint:
                                valid_point = False
                                break
                            elif constraint_type == "Distance" and distance_km > max_constraint:
                                valid_point = False
                                break
                        else:
                            valid_point = False
                            break
                    except Exception as e:
                        # Récupérer silencieusement en cas d'erreur API
                        error_msg = str(e)
                        if "API_RATE_LIMIT_EXCEEDED" in error_msg:
                            # Afficher un avertissement et retourner le meilleur point
                            # qui a le plus d'adresses prises en compte
                            st.warning("Limite d'API atteinte. Le meilleur point trouvé avec les données disponibles sera renvoyé.")
                            if potential_points:
                                # Trier par nombre d'adresses prises en compte puis par score
                                best_points = sorted(potential_points, key=lambda x: (-len(x['times']), x['score']))
                                return best_points[0]
                            return None
                        
                        # Pour les autres erreurs, on continue avec le point suivant
                        valid_point = False
                        break
                
                # Si le point est valide et que toutes les adresses sont prises en compte
                if valid_point and len(times) == len(coords):
                    successful_points += 1
                    # Calculate score - we want to minimize the maximum travel time/distance
                    if constraint_type == "Time":
                        score = max(times)
                    else:
                        score = max(distances)
                    
                    potential_points.append({
                        'point': point,
                        'score': score,
                        'times': times,
                        'distances': distances
                    })
    
    # Find the best point (lowest score)
    if potential_points:
        best_point = min(potential_points, key=lambda x: x['score'])
        return best_point
    else:
        return None

# Function to create map
def create_map(addresses, coordinates, ideal_point=None, routes=None):
    # Calculate center of coordinates for map
    if coordinates:
        center_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
        center_lon = sum(coord[1] for coord in coordinates) / len(coordinates)
    else:
        # Default center (Paris, France)
        center_lat, center_lon = 48.8566, 2.3522
    
    # Create map
    m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
    
    # Add markers for each address
    for i, (address, coord) in enumerate(zip(addresses, coordinates)):
        folium.Marker(
            location=coord,
            popup=address,
            tooltip=f"Address {i+1}: {address}",
            icon=folium.Icon(color='blue', icon='home')
        ).add_to(m)
    
    # Add ideal meeting point if available
    if ideal_point:
        folium.Marker(
            location=ideal_point['point'],
            popup=f"Ideal Meeting Point<br>Max Time: {max(ideal_point['times']):.1f} min<br>Max Distance: {max(ideal_point['distances']):.1f} km",
            tooltip="Ideal Meeting Point",
            icon=folium.Icon(color='red', icon='flag')
        ).add_to(m)
    
    # Add routes if available
    if routes:
        for i, route in enumerate(routes):
            try:
                if route and 'features' in route and len(route['features']) > 0:
                    # Pour format GeoJSON
                    geometry = route['features'][0]['geometry']
                    if geometry['type'] == 'LineString':
                        # Transformation des coordonnées [lon, lat] en [lat, lon] pour folium
                        coordinates = [[point[1], point[0]] for point in geometry['coordinates']]
                        # Ajouter l'itinéraire à la carte
                        folium.PolyLine(
                            coordinates,
                            color='green',
                            weight=4,
                            opacity=0.7,
                            tooltip=f"Route from {addresses[i]}"
                        ).add_to(m)
                elif route and 'routes' in route and len(route['routes']) > 0 and 'geometry' in route['routes'][0]:
                    # Pour l'ancien format
                    geometry = route['routes'][0]['geometry']
                    decoded = polyline.decode(geometry)
                    # Ajouter l'itinéraire à la carte
                    folium.PolyLine(
                        decoded,
                        color='green',
                        weight=4,
                        opacity=0.7,
                        tooltip=f"Route from {addresses[i]}"
                    ).add_to(m)
            except Exception:
                # Erreur silencieuse
                pass
    
    return m

# Process button
col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    find_button = st.button("Trouver le point de rencontre", use_container_width=True)

if find_button:
    # Validate input
    if not OPENROUTE_API_KEY:
        st.error("Veuillez entrer votre clé API OpenRoute Service dans la barre latérale")
    elif all(address.strip() for address in address_inputs):
        # Geocode addresses
        coordinates = []
        for address in address_inputs:
            coords = geocode_address(address)
            if coords:
                coordinates.append(coords)
        
        if len(coordinates) >= 2:
            # Afficher une barre de progression pendant le calcul
            with st.spinner("Calcul du point de rencontre idéal en cours..."):
                # Find ideal meeting point
                ideal_point = find_ideal_meeting_point(coordinates, transport_mode, constraint_type, max_constraint)
            
            # Vérification du résultat
            if ideal_point is None:
                st.warning("Impossible de trouver un point de rencontre idéal avec les contraintes actuelles. Essayez d'augmenter le temps/distance maximum.")
            else:
                # Vérifier que nous avons des temps et distances pour toutes les adresses
                if len(ideal_point['times']) != len(coordinates):
                    st.warning(f"Attention: seules {len(ideal_point['times'])}/{len(coordinates)} adresses ont été prises en compte dans le calcul.")
                
                # Get routes from each address to the meeting point
                routes = []
                
                for coord in coordinates:
                    try:
                        route = get_route(coord, ideal_point['point'], transport_mode)
                        routes.append(route)
                    except Exception:
                        # En cas d'erreur, ajouter None à la liste des routes
                        routes.append(None)
                
                # Create and display map
                m = create_map(address_inputs, coordinates, ideal_point, routes)
                
                # Afficher la carte
                folium_static(m)
                
                # Afficher le tableau récapitulatif des temps et distances
                col1, col2 = st.columns(2)
                
                # Préparer les données pour le tableau
                table_data = []
                
                for i, addr in enumerate(coordinates):
                    if i < len(ideal_point['times']):
                        table_data.append({
                            'Adresse': address_inputs[i],
                            'Temps de trajet (min)': f"{ideal_point['times'][i]:.1f}",
                            'Distance (km)': f"{ideal_point['distances'][i]:.1f}"
                        })
                    else:
                        table_data.append({
                            'Adresse': address_inputs[i],
                            'Temps de trajet (min)': "N/A",
                            'Distance (km)': "N/A"
                        })
                
                # Créer le DataFrame pour le tableau
                result_df = pd.DataFrame(table_data)
                
                # Résumé des résultats
                with col1:
                    st.markdown("### Résumé")
                    if len(ideal_point['times']) == len(coordinates):
                        st.markdown(f"**Distance maximale**: {max(ideal_point['distances']):.1f} km")
                        st.markdown(f"**Temps maximal**: {max(ideal_point['times']):.1f} min")
                    else:
                        st.markdown(f"**Distance maximale (pour les adresses calculées)**: {max(ideal_point['distances']):.1f} km")
                        st.markdown(f"**Temps maximal (pour les adresses calculées)**: {max(ideal_point['times']):.1f} min")
                    st.markdown(f"**Coordonnées du point de rencontre**: {ideal_point['point'][0]:.6f}, {ideal_point['point'][1]:.6f}")
                
                # Tableau détaillé
                with col2:
                    st.markdown("### Détails par adresse")
                    st.dataframe(result_df, use_container_width=True)
        else:
            st.error("Veuillez fournir au moins 2 adresses valides")
    else:
        st.error("Veuillez remplir tous les champs d'adresse")
