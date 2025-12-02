from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import json
import os
from main import FLLNexusConnector

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

# Config file path
CONFIG_FILE = 'config.json'

# Initialize FLL Nexus Connector
connector = FLLNexusConnector()

# Global state
current_overlay = "matchOverlay"
event_data = {
    "region": "socal",
    "event_id": "demo",
    "rankings": [],
    "sponsor_logos": []
}

def load_config():
    """Load configuration from file"""
    global event_data
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                event_data['region'] = config.get('region', 'socal')
                event_data['event_id'] = config.get('event_id', 'demo')
                event_data['event_name'] = config.get('event_name', '')
                print(f"Loaded config: {event_data['region']}/{event_data['event_id']}")
        except Exception as e:
            print(f"Error loading config: {e}")
    else:
        print("No config file found, using defaults")

def save_config():
    """Save configuration to file"""
    try:
        config = {
            'region': event_data['region'],
            'event_id': event_data['event_id'],
            'event_name': event_data.get('event_name', '')
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"Saved config: {event_data['region']}/{event_data['event_id']}")
    except Exception as e:
        print(f"Error saving config: {e}")

@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')

@app.route('/controller')
def controller():
    """Controller page for selecting overlay mode"""
    return render_template('controller.html')

@app.route('/setup')
def setup():
    """Event setup page"""
    return render_template('setup.html')

@app.route('/display')
def display():
    """Audience display page"""
    return render_template('display.html')

@app.route('/audio-test')
def audio_test():
    """Audio testing page"""
    return render_template('audio_test.html')

@app.route('/schedule')
def schedule():
    """Match schedule page"""
    return render_template('schedule.html')

@app.route('/scores')
def scores():
    """Team scores page"""
    return render_template('scores.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connection_established', {'client_id': request.sid})
    # Send current overlay selection
    emit('overlay_selection', {'screen': current_overlay})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('set_overlay')
def handle_set_overlay(data):
    """Handle overlay mode selection from controller"""
    global current_overlay
    current_overlay = data.get('screen', 'matchOverlay')
    print(f'Setting overlay to: {current_overlay}')
    # Broadcast to all connected displays
    emit('overlay_selection', {'screen': current_overlay}, broadcast=True)

@socketio.on('request_rankings')
def handle_request_rankings():
    """Fetch and send rankings data"""
    try:
        # Ensure we're authenticated
        if not connector.id_token:
            print("Not authenticated, attempting to load refresh token...")
            connector.load_refresh_token()

        region = event_data['region']
        event_id = event_data['event_id']

        print(f"Fetching rankings for {region}/{event_id}...")
        rankings = connector.get_team_scores_summary(region, event_id)

        # Sort by high score
        rankings_sorted = sorted(rankings, key=lambda x: x['high_score'], reverse=True)

        print(f"Successfully fetched {len(rankings_sorted)} teams")
        emit('rankings_data', {'rankings': rankings_sorted})
    except Exception as e:
        print(f"Error fetching rankings: {e}")
        emit('error', {'message': str(e)})

@socketio.on('request_event_info')
def handle_request_event_info():
    """Send current event information"""
    emit('event_info', event_data)

@socketio.on('set_event')
def handle_set_event(data):
    """Set the current event"""
    global event_data
    event_data['region'] = data.get('region', 'socal')
    event_data['event_id'] = data.get('event_id', 'demo')

    # Try to get event name
    try:
        if connector.id_token:
            events = connector.get_region_events(event_data['region'])
            if events and event_data['event_id'] in events:
                event_info = events[event_data['event_id']]
                if isinstance(event_info, dict):
                    event_data['event_name'] = event_info.get('name', event_data['event_id'])
    except Exception as e:
        print(f"Could not fetch event name: {e}")

    print(f"Event set to: {event_data['region']}/{event_data['event_id']}")

    # Save config to file
    save_config()

    emit('event_info', event_data, broadcast=True)

@socketio.on('timer_update')
def handle_timer_update(data):
    """Broadcast timer updates to all displays"""
    emit('timer_data', data, broadcast=True)

@socketio.on('load_events')
def handle_load_events(data):
    """Load events for a specific region"""
    try:
        # Ensure we're authenticated
        if not connector.id_token:
            print("Not authenticated, attempting to load refresh token...")
            connector.load_refresh_token()

        region = data.get('region', 'socal')
        print(f"Loading events for region: {region}")

        events = connector.get_region_events(region)

        if not events or not isinstance(events, dict):
            emit('events_list', {'error': 'No events found or unable to access events list'})
            return

        print(f"Found {len(events)} events in {region}")
        emit('events_list', {'events': events, 'region': region})

    except Exception as e:
        print(f"Error loading events: {e}")
        emit('events_list', {'error': str(e)})

@socketio.on('request_schedule')
def handle_request_schedule():
    """Fetch match schedule (sessions) for current event"""
    try:
        region = event_data['region']
        event_id = event_data['event_id']

        print(f"Fetching sessions for {region}/{event_id}...")
        sessions_data = connector.get_event_sessions(region, event_id)

        if not sessions_data:
            print("No sessions found")
            emit('schedule_data', {'schedule': [], 'event': event_data})
            return

        # Convert sessions dict to list with formatted data
        schedule = []
        for session_id, session_info in sessions_data.items():
            if isinstance(session_info, dict):
                session_entry = {
                    'session_id': session_id,
                    'time': session_info.get('time', 0),
                    'teams': session_info.get('teams', []),
                    'practice': session_info.get('practice', False),
                    'is_session': session_info.get('session', False)
                }
                schedule.append(session_entry)

        # Sort by time
        schedule.sort(key=lambda x: x['time'])

        print(f"Successfully fetched {len(schedule)} sessions")
        emit('schedule_data', {'schedule': schedule, 'event': event_data})
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        emit('error', {'message': str(e)})

@socketio.on('request_scores')
def handle_request_scores():
    """Fetch detailed team scores for current event"""
    try:
        region = event_data['region']
        event_id = event_data['event_id']

        print(f"Fetching scores for {region}/{event_id}...")
        scores = connector.get_team_scores_summary(region, event_id)

        print(f"Successfully fetched scores for {len(scores)} teams")
        emit('scores_data', {'scores': scores, 'event': event_data})
    except Exception as e:
        print(f"Error fetching scores: {e}")
        emit('error', {'message': str(e)})

if __name__ == '__main__':
    # Load saved configuration
    load_config()

    # Try to authenticate with saved token
    try:
        connector.load_refresh_token()
        print("Successfully authenticated with saved token")
    except Exception as e:
        print(f"Warning: Could not load refresh token: {e}")
        print("You may need to authenticate manually")

    print("\n" + "="*60)
    print("FLL Nexus Display Server")
    print("="*60)
    print("Controller: http://localhost:5001/controller")
    print("Display:    http://localhost:5001/display")
    print("="*60 + "\n")

    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
