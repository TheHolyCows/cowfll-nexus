# FLL Nexus Tournament Management System

A comprehensive real-time tournament management system for FIRST LEGO League competitions featuring audience displays with chroma key support, table displays, match scheduling, and live rankings integration.

## Features

### 🎮 Controller Dashboard
- **Unified control panel** for managing all displays and tournament operations
- **Real-time display mode switching** (Match Overlay, Rankings, Sponsors, Blank)
- **Match timer control** with audio cues (start bell, warning beep, stop buzzer)
- **Session control** for managing match schedules across table displays
- **Live status monitoring** (connection status, client counts, last rankings update)
- **Authentication management** with token expiry tracking

### 📺 Audience Display
- **Chroma key ready** - Magenta (#ff00ff) background for video mixing
- **Match overlay mode** - Timer, event info, and team assignments for up to 4 tables
- **Rankings display** - Full-screen auto-scrolling rankings table
- **Sponsor slideshow** - Rotating sponsor logos with smooth transitions
- **Auto-refresh rankings** every 15 seconds (pauses during active matches)
- **Match-aware timing** - Automatically pauses rankings refresh during matches

### 🖥️ Table Display
- **Individual table screens** showing team information per table
- **Unlimited table support** - Dynamically detects tables from schedule
- **Table selection screen** - Choose which table each display represents
- **Session synchronization** - All tables update together via controller
- **Dynamic font sizing** - Automatically adjusts for long team names
- **Match schedule display** - Shows session number and time

### 📊 Data Management
- **Match schedule viewer** - Sortable table view of all sessions
- **Team scores viewer** - Rankings with detailed scoring information
- **Live FLL Nexus integration** - Real-time data synchronization
- **OAuth authentication** - Secure login with token management
- **Event selection** - Choose region and event dynamically

## Project Structure

```
nexus-fll/
├── app.py                      # Flask + Socket.IO server
├── main.py                     # FLLNexusConnector API client
├── requirements.txt            # Python dependencies
├── templates/
│   ├── index.html             # Landing page
│   ├── controller.html        # Main control panel
│   ├── display.html           # Audience display (chroma key)
│   ├── table_display.html     # Individual table screens
│   ├── setup.html             # Event setup & authentication
│   ├── schedule.html          # Match schedule viewer
│   └── scores.html            # Team scores viewer
├── static/
│   ├── css/
│   │   ├── controller.css     # Shared controller styling
│   │   └── display.css        # Display styling (chroma key)
│   ├── images/
│   │   ├── flltm.svg          # FLL logo
│   │   ├── flllogo.svg        # Event logo
│   │   └── sponsors/          # Sponsor logos
│   └── audio/
│       ├── startbell.mp3      # Match start sound
│       ├── warning.mp3        # 30-second warning
│       └── stopbell.mp3       # Match end sound
└── firebase_refresh_token.txt # OAuth refresh token (generated on first auth)
```

## Setup

### Prerequisites
- Python 3.7 or higher
- Modern web browser with WebSocket support
- FLL Nexus account (for live data integration)

### Installation

1. **Clone the repository:**
   ```bash
   cd nexus-fll
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server:**
   ```bash
   python app.py
   ```

4. **Access the application:**
   - Landing page: http://localhost:5000
   - Controller: http://localhost:5000/controller
   - Event Setup: http://localhost:5000/setup

## Initial Setup

### 1. Authentication

1. Navigate to **Controller** → **Event Setup**
2. Click **🔐 Authenticate**
3. Log in with your FLL Nexus credentials
4. Your refresh token will be saved to `firebase_refresh_token.txt`
5. Token expiry is displayed and tracked automatically

### 2. Event Configuration

1. In **Event Setup**, enter your region (e.g., "socal", "norcal")
2. Click **📋 Load Events** to see available events
3. Select your event from the dropdown
4. Click **✓ Set Event** to configure the system
5. Rankings will automatically refresh

### 3. Display Setup

**For Audience Display:**
1. Open `/display` on the computer connected to your video mixer
2. Configure chroma key for magenta (#ff00ff) background
3. The display will show the selected mode from the controller

**For Table Displays:**
1. Open `/table_display` on each table screen
2. When first opened, you'll see a table selection screen
3. The system automatically detects the number of tables from your schedule
4. Click the appropriate table button for each screen (supports unlimited tables)
5. Use the controller to navigate sessions

## Usage Guide

### Running a Tournament

#### Before Matches Start
1. Open **Controller** on your control station
2. Open **Audience Display** on your video mixer computer
3. Open **Table Display** on each table screen (if using)
4. Set the current event in **Event Setup**
5. Switch audience display to **Rankings** or **Sponsors**

#### Running a Match
1. In the controller, use **Session Control** to select the current match
2. Table displays will update to show team assignments
3. Click **▶️ Start Match** to begin the countdown
4. The display automatically switches to **Match Overlay** mode
5. Audio cues play at key times:
   - **Start bell** - Match begins (2:29)
   - **Warning beep** - 30 seconds remaining
   - **Stop buzzer** - Match ends (0:00)
6. Use **⏸️ Pause** to pause if needed
7. Use **🔄 Reset** to reset the timer

#### Between Matches
1. Switch to **Rankings** to show current standings
2. Rankings auto-refresh every 15 seconds
3. Use **Session Control** arrows to advance to next match
4. Table displays update automatically

### Controller Features

#### Quick Navigation
- **Event Setup** - Configure event and authentication
- **Audience Display** - Open audience display window
- **Table Display** - Open table display window
- **Match Schedule** - View full tournament schedule
- **Team Scores** - View detailed rankings and scores

#### Audience Display Control
Select the display mode:
- **Match Overlay** - Show timer and team info during matches
- **Rankings** - Display current team standings
- **Sponsors** - Show sponsor slideshow
- **Blank Screen** - Hide all overlays (chroma key only)

#### Timer Controls
- **▶️ Start** - Begin countdown (auto-switches to match overlay)
- **⏸️ Pause** - Pause the timer
- **🔄 Reset** - Reset to 2:30

#### Session Control
- **⬅️ Previous** - Go to previous match
- **Next ➡️** - Advance to next match
- **Jump to Session** - Select specific session from dropdown

#### System Status
- **Last Rankings Update** - Timestamp of last data refresh
- **🔄 Refresh Rankings Now** - Manually fetch latest data

### Display Modes

#### Match Overlay
- Timer with color coding:
  - White: >30 seconds
  - Yellow: 10-30 seconds
  - Red: <10 seconds
- Event name and logos
- Team assignments for up to 4 tables
- Lower third showing team numbers and names

#### Rankings
- Full-screen table with:
  - Rank
  - Team Number
  - Team Name
  - High Score
  - Average Score
  - Rounds Played
- Sticky header while scrolling
- Auto-scroll through all teams
- Pauses during active matches

#### Sponsors
- Rotating sponsor logos
- 5-second display per sponsor
- Smooth fade transitions
- Customizable logo set

## Customization

### Adding Sponsor Logos

1. Add SVG files to `static/images/sponsors/`
2. Edit `display.html` line ~501:
   ```javascript
   sponsorLogos = ['flllogo.svg', 'viasat.svg', 'your-logo.svg'];
   ```

### Changing Chroma Key Color

Edit `static/css/display.css`:
```css
body {
    background-color: #ff00ff; /* Change to your preferred color */
}
```

### Adjusting Timer Duration

Edit `controller.html`:
```javascript
let currentSeconds = 150; // 2:30 in seconds (change as needed)
```

### Customizing Audience Display Table Count

The audience display match overlay shows 4 tables by default in the lower third. To change this, edit `display.html` line ~481:
```javascript
const tables = ['Table 1', 'Table 2', 'Table 3', 'Table 4']; // Add/remove tables for audience view
```

**Note:** Individual table displays support unlimited tables automatically based on your schedule data.

### Changing Audio Files

Replace files in `static/audio/`:
- `startbell.mp3` - Match start sound
- `warning.mp3` - 30-second warning
- `stopbell.mp3` - Match end sound

## WebSocket Events

### Client → Server
- `register_client` - Register display type (audience_display, table_display)
- `set_overlay` - Change audience display mode
- `timer_update` - Update match timer
- `request_rankings` - Fetch fresh rankings data
- `request_schedule` - Fetch match schedule
- `request_scores` - Fetch team scores
- `set_event` - Change event/region
- `load_events` - List available events
- `set_session` - Change current session
- `request_event_info` - Get current event info
- `request_user_info` - Get authentication status
- `logout` - Clear authentication

### Server → Client
- `connection_established` - Connection confirmation
- `overlay_selection` - Display mode update
- `timer_data` - Timer state update
- `rankings_data` - Rankings update
- `schedule_data` - Schedule update
- `scores_data` - Scores update
- `events_list` - Available events
- `event_info` - Current event information
- `user_info` - User authentication status
- `session_update` - Current session change
- `client_counts` - Connected client statistics
- `auth_status` - Authentication state
- `logout_success` - Logout confirmation

## Technical Details

### Architecture
- **Backend:** Flask + Flask-SocketIO for WebSocket communication
- **Frontend:** Vanilla JavaScript with Socket.IO client
- **Styling:** CSS3 with FLL brand colors and gradients
- **Real-time sync:** All displays update instantly via WebSockets

### Browser Compatibility
- Chrome/Edge (recommended)
- Firefox
- Safari
- Requires JavaScript and WebSocket support

### Network Requirements
- All devices must be on the same network
- Server broadcasts to all connected clients
- Minimal bandwidth required (WebSocket events are small)

### Performance
- Lightweight client-side rendering
- Efficient WebSocket communication
- Auto-cleanup of disconnected clients
- No database required (uses FLL Nexus API)

## Troubleshooting

### Display Not Updating
- Check connection status in controller (should show "Connected")
- Open browser console (F12) for error messages
- Verify all devices are on same network
- Refresh the page to reconnect WebSocket

### Authentication Issues
- Ensure you're using valid FLL Nexus credentials
- Check that `firebase_refresh_token.txt` exists and is readable
- Token expires after a period - re-authenticate if needed
- Check server logs for authentication errors

### Rankings Not Loading
- Verify authentication in Event Setup
- Confirm region and event_id are correct
- Check server logs for API errors
- Try clicking "🔄 Refresh Rankings Data"

### Timer Not Syncing
- Ensure controller is connected (check status indicator)
- Refresh audience display page
- Check browser console for WebSocket errors

### Audio Not Playing
- Click anywhere on the display page to enable audio (browser requirement)
- Check that audio files exist in `static/audio/`
- Verify browser audio is not muted

### Table Display Issues
- Ensure schedule data is loaded (check controller)
- Verify table parameter is correct (0-3)
- Check that session is selected in controller

## Development

### Running in Debug Mode
```bash
python app.py
```
Server runs on `http://0.0.0.0:5000` by default.

### Project Dependencies
- **Flask** - Web framework
- **Flask-SocketIO** - WebSocket support
- **python-socketio** - Socket.IO implementation
- **requests** - HTTP client for API calls
- **FLLNexusConnector** - Custom API client

### Adding New Features
1. Add WebSocket event handlers in `app.py`
2. Create frontend listeners in HTML templates
3. Update this README with new functionality

## Credits

Built for FIRST LEGO League tournaments.
Inspired by the CowFLLTM tournament management system.

## License

This project is provided as-is for FIRST LEGO League events.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review server logs for errors
3. Open browser console (F12) for client-side errors
4. Verify all setup steps are completed

---

**FLL Nexus Tournament Management System** - Professional tournament display solution for FIRST LEGO League competitions.
