import requests
import time
import json
from urllib.parse import urlparse, parse_qs

class FLLNexusConnector:
    def __init__(self):
        self.api_key = "AIzaSyC07mN9lu5AkZ4b5yod0S3vsdVjUPXjjRo"
        self.database_url = "https://nexus-fll-prod-default-rtdb.firebaseio.com"
        self.project_id = "nexus-fll-prod"
        self.id_token = None
        self.refresh_token = None
        self.token_expiry = 0
    
    def request_magic_link(self, email, redirect_url="https://fll.nexus/login?logout=true&redirect=%2Fprofile"):
        """Step 1: Request a magic link to be sent to email"""
        cloud_function_url = "https://us-central1-nexus-fll-prod.cloudfunctions.net/sendLoginEmail"
        
        response = requests.post(cloud_function_url, json={
            "data": {
                "email": email,
                "redirectUrl": redirect_url
            }
        })
        
        if response.status_code == 200:
            print(f"✓ Magic link sent to {email}")
            return True
        else:
            print(f"✗ Error: {response.status_code} - {response.text}")
            return False
    
    def sign_in_with_magic_link(self, email, magic_link):
        """Step 2: Complete sign-in using the magic link from email"""
        parsed = urlparse(magic_link)
        oob_code = parse_qs(parsed.query)['oobCode'][0]
        
        verify_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithEmailLink?key={self.api_key}"
        
        response = requests.post(verify_url, json={
            "email": email,
            "oobCode": oob_code
        })
        
        if response.status_code == 200:
            result = response.json()
            self.id_token = result['idToken']
            self.refresh_token = result['refreshToken']
            self.token_expiry = time.time() + int(result['expiresIn'])
            
            print(f"✓ Successfully signed in as {email}")
            return True
        else:
            print(f"✗ Sign-in error: {response.json()}")
            return False
    
    def load_refresh_token(self, filepath='firebase_refresh_token.txt'):
        """Load a saved refresh token"""
        try:
            with open(filepath, 'r') as f:
                self.refresh_token = f.read().strip()
            self._refresh_id_token()
            return True
        except FileNotFoundError:
            print(f"✗ No refresh token found at {filepath}")
            return False
    
    def save_refresh_token(self, filepath='firebase_refresh_token.txt'):
        """Save refresh token for future use"""
        with open(filepath, 'w') as f:
            f.write(self.refresh_token)
        print(f"✓ Refresh token saved to {filepath}")
    
    def _refresh_id_token(self):
        """Refresh the ID token using refresh token"""
        if not self.refresh_token:
            raise Exception("No refresh token available")
        
        refresh_url = f"https://securetoken.googleapis.com/v1/token?key={self.api_key}"
        
        response = requests.post(refresh_url, json={
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        })
        
        if response.status_code == 200:
            result = response.json()
            self.id_token = result['id_token']
            self.refresh_token = result['refresh_token']
            self.token_expiry = time.time() + int(result['expires_in'])
            print("✓ Token refreshed")
        else:
            raise Exception(f"Token refresh failed: {response.json()}")
    
    def _ensure_valid_token(self):
        """Check if token is valid, refresh if needed"""
        if not self.id_token:
            raise Exception("Not authenticated. Call sign_in_with_magic_link() first")
        
        if time.time() >= self.token_expiry - 300:  # Refresh 5 min before expiry
            self._refresh_id_token()
    
    def get_user_info(self):
        """Get information about the currently authenticated user"""
        self._ensure_valid_token()
        
        # Try to get user info from Firebase Auth
        user_info_url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={self.api_key}"
        response = requests.post(user_info_url, json={
            "idToken": self.id_token
        })
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error getting user info: {response.status_code} - {response.text}")
    
    def get_realtime_data(self, path):
        """
        Get data from Firebase Realtime Database
        
        Args:
            path: Database path (e.g., "users/userId" or "events")
        
        Returns:
            JSON data from the database
        """
        self._ensure_valid_token()
        
        # Remove leading slash if present
        path = path.lstrip('/')
        
        url = f"{self.database_url}/{path}.json?auth={self.id_token}"
        response = requests.get(url)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            error_msg = response.json().get('error', 'Permission denied')
            raise Exception(f"Permission denied for path '/{path}': {error_msg}")
        else:
            raise Exception(f"Error fetching data: {response.status_code} - {response.text}")
    
    def query_realtime_data(self, path, order_by=None, limit_to_first=None, limit_to_last=None, 
                           start_at=None, end_at=None, equal_to=None):
        """
        Query Firebase Realtime Database with filters
        
        Args:
            path: Database path
            order_by: Field to order by (must be indexed)
            limit_to_first: Limit to first N results
            limit_to_last: Limit to last N results
            start_at: Start at this value
            end_at: End at this value
            equal_to: Equal to this value
        """
        self._ensure_valid_token()
        
        path = path.lstrip('/')
        url = f"{self.database_url}/{path}.json"
        
        params = {"auth": self.id_token}
        
        if order_by:
            params['orderBy'] = json.dumps(order_by)
        if limit_to_first:
            params['limitToFirst'] = limit_to_first
        if limit_to_last:
            params['limitToLast'] = limit_to_last
        if start_at is not None:
            params['startAt'] = json.dumps(start_at)
        if end_at is not None:
            params['endAt'] = json.dumps(end_at)
        if equal_to is not None:
            params['equalTo'] = json.dumps(equal_to)
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error querying data: {response.status_code} - {response.text}")
    
    def get_region_events(self, region):
        """Get all events for a specific region"""
        return self.get_realtime_data(f"regionSummaries/{region}/events")
    
    def get_region_summary(self, region):
        """Get summary data for a specific region"""
        return self.get_realtime_data(f"regionSummaries/{region}")
    
    def list_region_summaries(self):
        """List all region summaries"""
        return self.get_realtime_data("regionSummaries")
    
    def get_event_teams(self, region, event_id):
        """Get teams for a specific event"""
        return self.get_realtime_data(f"regions/{region}/events/{event_id}/teams")
    
    def get_team_scores_summary(self, region, event_id):
        """
        Get a formatted summary of all team scores for an event
        Returns a list of dicts with team info and scores
        """
        teams = self.get_event_teams(region, event_id)
        if not teams or not isinstance(teams, dict):
            return []
        
        results = []
        for team_id, team_data in teams.items():
            if isinstance(team_data, dict):
                team_info = {
                    'team_id': team_id,
                    'team_number': team_data.get('teamNumber', team_id),
                    'name': team_data.get('name', 'Unknown'),
                    'scores': team_data.get('scores', {}),
                }
                
                # Calculate additional stats
                if team_info['scores']:
                    # Handle both list and dict formats for scores
                    if isinstance(team_info['scores'], dict):
                        score_values = [v for v in team_info['scores'].values() if isinstance(v, (int, float))]
                    elif isinstance(team_info['scores'], list):
                        score_values = [v for v in team_info['scores'] if isinstance(v, (int, float))]
                    else:
                        score_values = []

                    if score_values:
                        team_info['high_score'] = max(score_values)
                        team_info['average_score'] = sum(score_values) / len(score_values)
                        team_info['total_rounds'] = len(score_values)
                    else:
                        team_info['high_score'] = 0
                        team_info['average_score'] = 0
                        team_info['total_rounds'] = 0
                else:
                    team_info['high_score'] = 0
                    team_info['average_score'] = 0
                    team_info['total_rounds'] = 0
                
                results.append(team_info)
        
        return results
    
    def get_event_sessions(self, region, event_id):
        """Get game sessions for a specific event"""
        return self.get_realtime_data(f"regions/{region}/events/{event_id}/games/sessions")
    
    def get_event_games(self, region, event_id):
        """Get all games data for a specific event"""
        return self.get_realtime_data(f"regions/{region}/events/{event_id}/games")
    
    def get_session_matches(self, region, event_id, session_id):
        """Get matches for a specific session"""
        return self.get_realtime_data(f"regions/{region}/events/{event_id}/games/sessions/{session_id}/matches")
    
    def get_event_data(self, region, event_id):
        """Get all data for a specific event"""
        return self.get_realtime_data(f"regions/{region}/events/{event_id}")
    
    def get_event_scores(self, region, event_id):
        """Get scores for a specific event (if available)"""
        return self.get_realtime_data(f"regions/{region}/events/{event_id}/scores")
    
    def get_event_rankings(self, region, event_id):
        """Get rankings for a specific event (if available)"""
        return self.get_realtime_data(f"regions/{region}/events/{event_id}/rankings")
    
    def list_regions(self):
        """List all available regions"""
        return self.get_realtime_data("regions")
    
    def list_paths(self, path, shallow=True):
        """
        List keys at a path without fetching full data
        
        Args:
            path: Database path
            shallow: If True, only returns keys
        """
        self._ensure_valid_token()
        
        path = path.lstrip('/')
        url = f"{self.database_url}/{path}.json"
        params = {
            "auth": self.id_token,
            "shallow": "true" if shallow else "false"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error listing paths: {response.status_code} - {response.text}")


# Example usage
if __name__ == "__main__":
    connector = FLLNexusConnector()
    
    # First time setup
    email = "kchau@vivid-hosting.net"
    
    # Try to load existing refresh token
    if not connector.load_refresh_token():
        # If no saved token, do the magic link flow
        connector.request_magic_link(email)
        
        print("\nCheck your email and paste the magic link URL here:")
        magic_link = input().strip()
        
        if connector.sign_in_with_magic_link(email, magic_link):
            connector.save_refresh_token()
    
    # Now you're authenticated and can access data
    print("\n--- Fetching data ---")
    
    # First, get your user info to find your user ID
    try:
        user_info = connector.get_user_info()
        user_id = user_info['users'][0]['localId']
        user_email = user_info['users'][0]['email']
        print(f"\nAuthenticated as: {user_email}")
        print(f"User ID: {user_id}")
        
        # Example: Try the path structure you found
        print("\n" + "="*60)
        print("Example: Fetching SoCal regional data")
        print("="*60)
        try:
            region = "socal"
            
            # First, list all available events in the region
            print(f"\nListing all {region} events:")
            events = connector.get_region_events(region)
            
            if not events or not isinstance(events, dict):
                print("No events found or unable to access events list")
            else:
                print(f"✓ Found {len(events)} events:")
                event_list = []
                for i, (event_id, event_data) in enumerate(events.items(), 1):
                    event_name = event_data.get('name', event_id) if isinstance(event_data, dict) else event_id
                    print(f"  {i}. {event_id} - {event_name}")
                    event_list.append(event_id)
                
                # Ask user to select an event
                print("\nEnter the number of the event you want to fetch (or press Enter to skip):")
                choice = input().strip()
                
                if choice:
                    try:
                        event_index = int(choice) - 1
                        if event_index < 0 or event_index >= len(event_list):
                            print("Invalid selection")
                        else:
                            event_id = event_list[event_index]
                            
                            print(f"\n--- Fetching data for event: {event_id} ---")
                            
                            # Get teams for the selected event
                            print(f"\nFetching teams for {event_id}:")
                            teams = connector.get_event_teams(region, event_id)
                            if teams:
                                print(f"✓ Found teams")
                                if isinstance(teams, dict):
                                    print(f"  Total teams: {len(teams)}")
                                    # Show first few teams with scores
                                    for i, (team_id, team_data) in enumerate(list(teams.items())[:5]):
                                        team_name = team_data.get('name', 'N/A')
                                        team_number = team_data.get('teamNumber', 'N/A')
                                        scores = team_data.get('scores', {})
                                        print(f"  - #{team_number}: {team_name}")
                                        if scores:
                                            print(f"    Scores: {scores}")
                                    if len(teams) > 5:
                                        print(f"  ... and {len(teams) - 5} more")
                            
                            # Get formatted score summary
                            print(f"\nGetting score summary for {event_id}:")
                            score_summary = connector.get_team_scores_summary(region, event_id)
                            if score_summary:
                                print(f"✓ Score summary for {len(score_summary)} teams")
                                # Sort by high score
                                sorted_teams = sorted(score_summary, key=lambda x: x['high_score'], reverse=True)
                                print("\nTop 5 teams by high score:")
                                for i, team in enumerate(sorted_teams[:5], 1):
                                    print(f"  {i}. #{team['team_number']}: {team['name']}")
                                    print(f"     High: {team['high_score']}, Avg: {team['average_score']:.1f}, Rounds: {team['total_rounds']}")
                            
                            # Get game sessions
                            print(f"\nFetching game sessions for {event_id}:")
                            sessions = connector.get_event_sessions(region, event_id)
                            if sessions:
                                print(f"✓ Found sessions")
                                if isinstance(sessions, dict):
                                    print(f"  Total sessions: {len(sessions)}")
                                    for i, (session_id, session_data) in enumerate(list(sessions.items())[:3]):
                                        print(f"  - {session_id}: {session_data}")
                                        if i >= 2 and len(sessions) > 3:
                                            print(f"  ... and {len(sessions) - 3} more")
                                            break
                    except ValueError:
                        print("Invalid input")
                else:
                    print("Skipping event data fetch")
            
        except Exception as e:
            print(f"Error accessing regional data: {e}")
        
    except Exception as e:
        print(f"Error: {e}")
