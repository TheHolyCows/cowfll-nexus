from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import json
from main import FLLNexusConnector

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*")

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

@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')

@app.route('/controller')
def controller():
    """Controller page for selecting overlay mode"""
    return render_template('controller.html')

@app.route('/display')
def display():
    """Audience display page"""
    return render_template('display.html')

@app.route('/audio-test')
def audio_test():
    """Audio testing page"""
    return render_template('audio_test.html')

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

if __name__ == '__main__':
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
