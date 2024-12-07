from flask_socketio import SocketIO, emit
from openrouteservice import convert, Client
from flask import Flask, render_template, session, request

import google.generativeai as genai
import os
import re
import json
from dotenv import load_dotenv
import googlemaps
import folium
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# Define API keys
load_dotenv('./.env')
ORS_API_key = os.getenv('ORS_APIKEY')
GMAP_API_key = os.getenv('GMAP_APIKEY')
GEMINI_API_key = os.getenv('GEMINI_APIKEY')

genai.configure(api_key=GEMINI_API_key)
generation_config = {
    "temperature": 0,
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 5000,
    "response_mime_type": "text/plain",
}

llm = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_secret_key")
socketio = SocketIO(app, ping_interval=25, ping_timeout=70, cors_allowed_origins="*", engineio_logger=True, logger=True, max_http_buffer_size=15000000)

# Establish respective map and routing clients
GMAPS_client = googlemaps.Client(GMAP_API_key)
ORS_client = Client(ORS_API_key)

history = []
start_location = None
end_location = None
vehicle_type = None

@app.route('/')
def index():
    """
    Serve the main HTML page and reset the chat history for a new session.
    """
    return render_template('index.html')  # Serve the HTML page

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")

@socketio.on('vehicleTypeSelected')
def handle_vehicle_type_selected(data: str):
    global vehicle_type
    vehicle_type = data
    print(f"Vehicle Type Selected: {data}")

@socketio.on('location')
def handle_location(data):
    global end_location, start_location
    end_location = data.get('end')
    start_location = data.get('start')
    print(f"Locations set - Start: {start_location}, End: {end_location}")

@socketio.on('transcript')
def extract_location_info(data):
    global start_location, end_location, vehicle_type

    # Append the user's transcript to the history with the correct structure
    history.append({"role": "user", "parts": [data]})

    # Prepare the prompt instructions
    prompt = f"""
    You are a Malaysian transportation planner for the company Setel and you need to plan a route for a user who wants to travel from one location to another. Thus:
    1. Ask the user for the start and end locations of their trip (if not yet given in the chat history). Include start: <start_location>, end: <end_location> at the end of your response.
    2. Ask the user for the type of vehicle they would like to use for the trip (either public or private only, if not yet given in the chat history). Include vehicle: <vehicle_type> at the end of your response.
    3. Based on the provided routes, generate a friendly message that tells the user all their available options, costs, and time estimates. There might be more than one path, recommend the fastest path but also provide the user with other options.
    4. Follow up with the user if they need any further assistance.
    5. Keep your responses friendly and concise.
    6. For public transport options, you can recommend the user 3 different passes: the 1 day pass for RM6, the 3 day pass for RM20, and the 30 day pass for RM50.
    7. Do not suggest anything as long as the user has not provided the necessary information (start and end locations, vehicle type).

    Give your response in the format: 
    
    You can take the bus from <start_location> to <end_location>. The trip will take approximately 1 hour and cost RM3.50. Would you like to know more about the 3 day pass? 
    start: <start_location>, end: <end_location> vehicle: <vehicle_type>

    The user transcript is: {data}
    Keep your response in 5 sentences or less.
    """

    # Append the prompt to the history with the correct structure
    history.append({"role": "user", "parts": [prompt]})

    # Start the chat session with the current history
    chat_session = llm.start_chat(history=history)

    # Send a message to get the model's response
    response = chat_session.send_message("Please provide a response now.")
    print(f"Response: {response.text}")

    # Append the model's response to the history
    history.append({"role": "model", "parts": [response.text]})

    try:
        # Regex patterns for parsing
        location_pattern = re.compile(
            r'start:\s*(?P<start>.+?),\s*end:\s*(?P<end>.+?)(?=\s*(vehicle:|$))',
            re.IGNORECASE
        )
        vehicle_pattern = re.compile(
            r'vehicle:\s*(?P<vehicle>.+?)(?=$)',
            re.IGNORECASE
        )

        # Reset global vars to ensure fresh extraction
        start_location = None
        end_location = None
        vehicle_type = None

        # Match and extract locations
        loc_match = location_pattern.search(response.text)
        if loc_match:
            start_location = loc_match.group('start').strip()
            end_location = loc_match.group('end').strip()

        # Match and extract vehicle type
        veh_match = vehicle_pattern.search(response.text)
        if veh_match:
            vehicle_type = veh_match.group('vehicle').strip().lower()  # convert to lower for easy comparison

        # Remove the start/end/vehicle lines from the final message
        main_response = response.text.split('start:', 1)[0].strip()

        # Emit extracted data if available
        if start_location and end_location:
            emit('stt-location', {"start": start_location, "end": end_location})
        if vehicle_type:
            emit('vehicle-type', {"vehicle": vehicle_type})

        # Check if all info provided
        if start_location and end_location and vehicle_type:
            if vehicle_type in ('public transport', 'lrt', 'public'):
                # Show LRT (public) route
                lrt_map_html = handle_public_transport(start_location, end_location)
                emit('map-updated', {"html": lrt_map_html})
            else:
                # Not public transport: we will default to sedan.
                # The client JS already fetches /map to get the private vehicle route map.
                # We'll rely on /map route to do additional LLM processing once the route is computed.
                # emit('response', {"message": main_response})
                pass
        else:
            # Just emit the main response
            emit('response', {"message": main_response})

        return start_location, end_location, vehicle_type
    
    except Exception as e:
        print(f"Error extracting location info: {e}")
        emit('response', {"message": response.text.strip()})


@app.route('/map', methods=['POST'])
def show_map():
    global vehicle_type
    try:
        data = request.get_json()
        start = data.get('start', start_location)
        end = data.get('end', end_location)

        start_location_dict = GMAPS_client.geocode(address=start)
        planned_loc = start_location_dict[0]['geometry']['location']
        start_lat, start_long = planned_loc.values()

        end_location_dict = GMAPS_client.geocode(address=end)
        end_loc = end_location_dict[0]['geometry']['location']
        end_lat, end_long = end_loc.values()

        # Calculate midpoint
        midpoint = ((start_lat + end_lat) / 2 , (start_long + end_long) / 2)

        # Setup folium map for private route viewing
        my_map = folium.Map(location=midpoint, zoom_start=12)
        start_marker = folium.Marker(location=[start_lat, start_long], icon=folium.Icon(color='blue'))
        end_marker = folium.Marker(location=[end_lat, end_long], icon=folium.Icon(color='red'))
        for marker in [start_marker, end_marker]:
            marker.add_to(my_map)

        # Determine optimized route for user
        # We'll request alternative routes for variety, just like done previously
        routes = ORS_client.directions(
            coordinates=[[start_long, start_lat], [end_long, end_lat]],
            profile='driving-car',
            alternative_routes={"share_factor": 0.6, "target_count": 2},
            format="geojson"
        )

        route_features = routes['features']
        route_colors = ['red', 'blue', 'green']
        route_distances_in_km = []
        route_time_in_mins = []

        for i, feature in enumerate(route_features):
            route_coords = [(coord[1], coord[0]) for coord in feature['geometry']['coordinates']]
            route_geom = folium.PolyLine(locations=route_coords,
                                         color=route_colors[i],
                                         weight=5,
                                         opacity=0.8,
                                         tooltip=f"Route {i + 1}: {feature['properties']['summary']}")
            route_geom.add_to(my_map)

            dist_km = round(feature['properties']['summary']['distance'] / 1000, 1)
            t_mins = int(feature['properties']['summary']['duration']) // 60
            route_distances_in_km.append(dist_km)
            route_time_in_mins.append(t_mins)

        # If not public transport, default to sedan
        if vehicle_type not in ('public transport', 'lrt', 'public'):
            vehicle_type = 'sedan'

        # Vehicle category dictionary
        vehicle_category_dict = {
            'sedan': {'fuel_consumption': 5, 'allowed_fuel': ['RON95', 'RON97']},
            'hatchback': {'fuel_consumption': 6.5, 'allowed_fuel': ['RON95', 'RON97']},
            'suv': {'fuel_consumption': 8.5, 'allowed_fuel': ['RON95', 'RON97', 'Diesel Euro 5 B10/B20', 'Diesel Euro 5 B7']},
            'motorcycle': {'fuel_consumption': 3, 'allowed_fuel': ['RON95', 'RON97']},
            'heavy duty vehicle': {'fuel_consumption': 35, 'allowed_fuel': ['Diesel Euro 5 B10/B20', 'Diesel Euro 5 B7']}
        }

        # Gas price dictionary
        gas_price_dict = {
            'RON95': 2.05,
            'RON97': 3.19,
            'Diesel Euro 5 B10/B20': 2.95,
            'Diesel Euro 5 B7': 3.15
        }

        def calculate_rough_fuel_cost(v_type, distance_km):
            fuel_consumption = vehicle_category_dict[v_type]['fuel_consumption']
            litres_used = fuel_consumption * distance_km / 100
            rough_cost = {fuel: 'RM' + str(round(gas_price_dict[fuel]*litres_used, 2))
                          for fuel in vehicle_category_dict[v_type]['allowed_fuel']}
            return rough_cost

        # Choose the fastest route (the one with minimum travel time)
        min_time_index = route_time_in_mins.index(min(route_time_in_mins))
        fastest_distance = route_distances_in_km[min_time_index]
        fastest_time = route_time_in_mins[min_time_index]
        drive_travel_cost = calculate_rough_fuel_cost(vehicle_type, fastest_distance)

        # Current local time
        current_time = time.localtime()
        current_datetime = datetime.fromtimestamp(time.mktime(current_time))
        new_datetime_drive = current_datetime + timedelta(minutes=fastest_time)
        formatted_time_drive = new_datetime_drive.strftime("%H:%M")

        # Now call LLM to provide a recommendation based on the private vehicle route
        chat_session = llm.start_chat(history=history)
        # We provide the details of the fastest route to LLM:
        llm_prompt = f"""
        The user is traveling by {vehicle_type} from {start} to {end}.
        The fastest route is {fastest_distance} km and takes about {fastest_time} minutes.
        The estimated fuel cost options are: {drive_travel_cost}.
        It is currently {current_datetime.strftime('%H:%M')} and arrival time is approximately {formatted_time_drive}.
        Generate a recommendation for the user based on this private vehicle route information. Keep your response in 5 sentences or less.
        """
        llm_response = chat_session.send_message(llm_prompt)
        print(f"LLM Private Route Response: {llm_response.text}")

        # Emit the LLM response to the frontend
        socketio.emit('response', {"message": llm_response.text})

        return my_map._repr_html_()
    
    except Exception as e:
        print(f"Error plotting map: {e}")
        return "Processing..."


def handle_public_transport(start, end):
    # Get coordinates
    start_location_dict = GMAPS_client.geocode(address=start)
    planned_loc = start_location_dict[0]['geometry']['location']
    start_lat, start_long = planned_loc.values()

    end_location_dict = GMAPS_client.geocode(address=end)
    end_loc = end_location_dict[0]['geometry']['location']
    end_lat, end_long = end_loc.values()

    # Get the current local time
    current_time = time.localtime()
    current_datetime = datetime.fromtimestamp(time.mktime(current_time))
    
    # Read in data for train routes
    fares_df = pd.read_csv('./files/Fare.csv').set_index('Unnamed: 0')
    routes_df = pd.read_csv('./files/Route.csv').set_index('Unnamed: 0')
    time_df = pd.read_csv('./files/Time.csv').set_index('Unnamed: 0')

    # Get station coordinates
    station_coords_dict = {
        name: GMAPS_client.geocode(address=f"{name} train station in Kuala Lumpur")[0]['geometry']['location']
        for name in fares_df.columns
    }

    def get_station_dist_from_location(lat, long):
        start2station_distances = []
        station_coords_array = [list(station_coords_dict[station].values()) for station in station_coords_dict.keys()]

        for coords in station_coords_array:
            station_lat, station_long = coords
            eucld_dist = np.sqrt((station_long - long)**2 + (station_lat - lat)**2)
            start2station_distances.append(eucld_dist)

        distance_df = pd.DataFrame()
        distance_df['Station'] = station_coords_dict.keys()
        distance_df['Distance'] = start2station_distances
        return distance_df

    start_station_distances_df = get_station_dist_from_location(start_lat, start_long)
    end_station_distances_df = get_station_dist_from_location(end_lat, end_long)

    closest_start_station = start_station_distances_df.loc[start_station_distances_df['Distance'].idxmin()]['Station']
    closest_end_station = end_station_distances_df.loc[end_station_distances_df['Distance'].idxmin()]['Station']

    train_travel_cost = float(fares_df.loc[closest_start_station][closest_end_station])
    train_route = routes_df.loc[closest_start_station][closest_end_station]
    train_time_taken = int(time_df.loc[closest_start_station][closest_end_station])

    new_datetime_train = current_datetime + timedelta(minutes=train_time_taken)
    formatted_time_train = new_datetime_train.strftime("%H:%M")

    socketio.emit('train-details', f"Route: {train_route}, Cost: RM{train_travel_cost}, ETA: {formatted_time_train} ({train_time_taken} mins)")

    # Start the chat session with the current history
    chat_session = llm.start_chat(history=history)
    response = chat_session.send_message(
        f"Generate a public transport route (only LRT, MRT, monorail) recommendation based on: {train_route}, cost RM{train_travel_cost}, arrival time {formatted_time_train}, {train_time_taken} mins. Keep your response in 5 sentences or less."
    )
    print(f"LRT LLM Response: {response.text}")
    socketio.emit('response', {"message": response.text})

    # Extract station names from the train route
    bracket_content = re.findall(r'\[(.*?)\]', train_route)
    extracted_stations = []
    for segment in bracket_content:
        stations = re.split(r' > ', segment)
        for station in stations:
            cleaned_station = station.strip()
            # Validate station is in route_df columns
            if cleaned_station in routes_df.columns:
                extracted_stations.append(cleaned_station)

    unique_stations = list(dict.fromkeys(extracted_stations))

    # Initialize the map for LRT route
    map2 = folium.Map(location=[3.1319, 101.6841], zoom_start=10)

    lines = []
    for station in unique_stations:
        coords = tuple(station_coords_dict[station].values())
        folium.Marker(location=coords, color='orange', popup=folium.Popup(station, parse_html=True)).add_to(map2)
        lines.append(coords)

    folium.PolyLine(locations=lines, color='red', weight=4, opacity=0.8, dash_array='5, 5').add_to(map2)
    return map2._repr_html_()


if __name__ == '__main__':
    # Run the Flask-SocketIO server on port 8899
    socketio.run(app, host="0.0.0.0", port=8899, allow_unsafe_werkzeug=True)