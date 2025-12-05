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
is_authenticated = False
current_session = None
event_data = {
    "region": "socal",
    "event_id": "demo",
    "rankings": [],
    "sponsor_logos": []
}

# Track connected clients by type
connected_clients = {
    'table_displays': set(),  # Session IDs of connected table displays
    'audience_displays': set()  # Session IDs of connected audience displays
}

def check_authentication():
    """Check if the connector is authenticated"""
    global is_authenticated
    # Check if we have a valid token
    is_authenticated = connector.id_token is not None
    return is_authenticated

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

@app.route('/auth')
def auth():
    """Authentication page"""
    return render_template('auth.html')

@app.route('/table_display')
def table_display():
    """Table display page for showing team info at specific tables"""
    return render_template('table_display.html')

@app.route('/api/sponsor_logos')
def get_sponsor_logos():
    """Get list of sponsor logo files"""
    try:
        sponsor_dir = os.path.join(app.static_folder, 'images', 'sponsors')
        if os.path.exists(sponsor_dir):
            # Get all SVG files in the sponsors directory
            files = [f for f in os.listdir(sponsor_dir) if f.endswith('.svg')]
            return {'logos': files}
        else:
            return {'logos': []}
    except Exception as e:
        print(f"Error listing sponsor logos: {e}")
        return {'logos': []}

def broadcast_client_counts():
    """Broadcast current client counts to all controllers"""
    counts = {
        'table_displays': len(connected_clients['table_displays']),
        'audience_displays': len(connected_clients['audience_displays'])
    }
    emit('client_counts', counts, broadcast=True)

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connection_established', {'client_id': request.sid})
    # Send current overlay selection (only to this client, not broadcast)
    emit('overlay_selection', {'screen': current_overlay}, room=request.sid)
    # Send authentication status
    emit('auth_status', {'authenticated': check_authentication()})
    # Send current session
    emit('current_session', {'session': current_session})
    # Send current client counts
    emit('client_counts', {
        'table_displays': len(connected_clients['table_displays']),
        'audience_displays': len(connected_clients['audience_displays'])
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')
    # Remove from tracking sets
    connected_clients['table_displays'].discard(request.sid)
    connected_clients['audience_displays'].discard(request.sid)
    # Broadcast updated counts
    broadcast_client_counts()

@socketio.on('register_client')
def handle_register_client(data):
    """Register a client as a specific type (table_display or audience_display)"""
    client_type = data.get('type')
    if client_type == 'table_display':
        connected_clients['table_displays'].add(request.sid)
        print(f'Registered table display: {request.sid} (Total: {len(connected_clients["table_displays"])})')
    elif client_type == 'audience_display':
        connected_clients['audience_displays'].add(request.sid)
        print(f'Registered audience display: {request.sid} (Total: {len(connected_clients["audience_displays"])})')

    # Broadcast updated counts to all clients
    broadcast_client_counts()

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
        # Broadcast to all clients so they can update their last refresh time
        emit('rankings_data', {'rankings': rankings_sorted}, broadcast=True)
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

@socketio.on('request_magic_link')
def handle_request_magic_link(data):
    """Request magic link for authentication"""
    try:
        email = data.get('email', '')
        if not email:
            emit('auth_error', {'message': 'Email is required'})
            return

        print(f"Requesting magic link for: {email}")
        success = connector.request_magic_link(email)

        if success:
            emit('magic_link_sent', {'email': email})
        else:
            emit('auth_error', {'message': 'Failed to send magic link'})
    except Exception as e:
        print(f"Error requesting magic link: {e}")
        emit('auth_error', {'message': str(e)})

@socketio.on('complete_auth')
def handle_complete_auth(data):
    """Complete authentication with magic link"""
    try:
        email = data.get('email', '')
        magic_link = data.get('magic_link', '')

        if not email or not magic_link:
            emit('auth_error', {'message': 'Email and magic link are required'})
            return

        print(f"Completing authentication for: {email}")
        success = connector.sign_in_with_magic_link(email, magic_link)

        if success:
            # Save refresh token
            connector.save_refresh_token()
            # Update authentication status
            global is_authenticated
            is_authenticated = True
            print("Authentication successful! Token saved.")
            emit('auth_success', {'message': 'Authentication successful!'})
            # Broadcast auth status to all clients
            emit('auth_status', {'authenticated': True}, broadcast=True)
        else:
            emit('auth_error', {'message': 'Authentication failed'})
    except Exception as e:
        print(f"Error completing authentication: {e}")
        emit('auth_error', {'message': str(e)})

@socketio.on('request_user_info')
def handle_request_user_info():
    """Get currently authenticated user info"""
    try:
        if not connector.id_token:
            # Try loading refresh token
            connector.load_refresh_token()

        if connector.id_token:
            user_info = connector.get_user_info()
            email = user_info['users'][0]['email']
            # Include token expiry timestamp
            emit('user_info', {
                'email': email,
                'authenticated': True,
                'token_expiry': connector.token_expiry
            })
        else:
            emit('user_info', {'authenticated': False})
    except Exception as e:
        print(f"Error getting user info: {e}")
        emit('user_info', {'authenticated': False})

@socketio.on('logout')
def handle_logout():
    """Logout and delete authentication token"""
    try:
        global is_authenticated
        is_authenticated = False
        connector.id_token = None
        connector.refresh_token = None

        # Delete the refresh token file
        import os
        if os.path.exists('firebase_refresh_token.txt'):
            os.remove('firebase_refresh_token.txt')
            print("Refresh token deleted")

        emit('logout_success', {'message': 'Successfully logged out'})
        # Broadcast auth status to all clients
        emit('auth_status', {'authenticated': False}, broadcast=True)
    except Exception as e:
        print(f"Error logging out: {e}")
        emit('error', {'message': str(e)})

@socketio.on('set_session')
def handle_set_session(data):
    """Set the current session for table displays"""
    global current_session
    current_session = data.get('session')
    print(f'Setting session to: {current_session}')
    # Broadcast to all connected table displays
    emit('session_update', {'session': current_session}, broadcast=True)

@socketio.on('request_current_session')
def handle_request_current_session():
    """Send the current session to requesting client"""
    emit('current_session', {'session': current_session})

@socketio.on('request_team_name')
def handle_request_team_name(data):
    """Fetch team name from scores data"""
    try:
        team_number = data.get('team_number')

        if not team_number:
            emit('team_name', {'team_number': None, 'name': 'Unknown Team'})
            return

        # Fetch scores to get team names
        region = event_data['region']
        event_id = event_data['event_id']

        scores = connector.get_team_scores_summary(region, event_id)

        # Find the team in scores
        team_name = None
        for team in scores:
            if str(team.get('team_number')) == str(team_number):
                team_name = team.get('name', f'Team {team_number}')
                break

        if not team_name:
            team_name = f'Team {team_number}'

        emit('team_name', {'team_number': team_number, 'name': team_name})
    except Exception as e:
        print(f"Error fetching team name: {e}")
        emit('team_name', {'team_number': team_number, 'name': f'Team {team_number}'})

if __name__ == '__main__':
    # Load saved configuration
    load_config()

    # Try to authenticate with saved token
    try:
        connector.load_refresh_token()
        is_authenticated = True
        print("Successfully authenticated with saved token")
    except Exception as e:
        is_authenticated = False
        print(f"Warning: Could not load refresh token: {e}")
        print("You will need to authenticate via the /auth page")

    print("\n" + "="*60)
    print("FLL Nexus Display Server")
    print("="*60)
    print("Controller:     http://localhost:5001/controller")
    print("Display:        http://localhost:5001/display")
    print("Table Display:  http://localhost:5001/table_display")
    print("Auth:           http://localhost:5001/auth")
    print("="*60 + "\n")

    socketio.run(app, debug=True, host='0.0.0.0', port=5001)
