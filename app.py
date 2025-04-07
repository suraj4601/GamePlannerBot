import os
import requests
import re
import time
from flask import Flask, request, jsonify, render_template, send_from_directory
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app with correct static folder configuration
app = Flask(__name__, static_folder='public', static_url_path='')
HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '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')
PORT = int(os.getenv('PORT', 3000))
USE_OFFLINE_MODE = False  # Set to False to use the API

def is_tournament_related(message):
    """Check if the message is related to tournament planning"""
    # If message is too short, likely not tournament-related
    if len(message.strip()) < 3:
        return False
        
    tournament_keywords = [
        'tournament', 'competition', 'match', 'game', 'player', 'team',
        'bracket', 'schedule', 'round', 'scoring', 'rules', 'format',
        'elimination', 'seed', 'ranking', 'leaderboard', 'prize',
        'registration', 'participant', 'venue', 'organize', 'plan',
        'esports', 'sports', 'gaming', 'event', 'championship',
        'knockout', 'finals', 'semifinals', 'quarterfinals',
        'swiss', 'robin', 'league', 'cup', 'trophy', 'contest',
        'sep', 'oct', 'nov', 'dec', 'jan', 'feb', 'mar', 'apr',
        'may', 'jun', 'jul', 'aug', 'date',
        # Additional gaming/tournament keywords
        'fixture', 'matchup', 'pairing', 'draw', 'seeding', 'group stage',
        'playoffs', 'ladder', 'qualifier', 'wildcard', 'bye', 'advancement',
        'lan', 'online', 'hybrid', 'host', 'streaming', 'spectator',
        'commentator', 'caster', 'referee', 'admin', 'marshal', 'judge',
        'gamer', 'competitive', 'casual', 'amateur', 'professional',
        'sponsorship', 'entry fee', 'registration fee', 'check-in',
        'best of', 'bo3', 'bo5', 'bo7', 'double elim', 'single elim',
        'map pool', 'map pick', 'veto', 'draft', 'ban', 'pick',
        'lobby', 'server', 'ping', 'discord', 'matchmaking', 'scrims',
        'practice', 'warm-up', 'cooldown', 'timeout', 'disqualification',
        'forfeit', 'walkover', 'results', 'standings', 'stats', 'mvp',
        'gaming', 'esport', 'fps', 'moba', 'rts', 'battle royale', 'card game',
        'board game', 'tabletop', 'rpg', 'fighting game', 'racing', 'simulation',
        'lol', 'dota', 'cs:go', 'valorant', 'overwatch', 'fortnite', 'pubg',
        'starcraft', 'hearthstone', 'mtg', 'yugioh', 'pokemon', 'smash bros',
        'fifa', 'madden', 'nba', 'nfl', 'mlb', 'nhl', 'chess', 'checkers',
        'go', 'backgammon', 'scrabble', 'catan', 'monopoly', 'risk',
        'livestream', 'twitch', 'youtube', 'facebook gaming', 'obs',
        'bracket generator', 'challonge', 'toornament', 'battlefy', 'smash.gg',
        'faceit', 'esl', 'dreamhack', 'major', 'minor', 'invitational',
        'season', 'offseason', 'preseason', 'regular season', 'exhibition',
        'showmatch', 'all-star', 'charity', 'fundraiser', 'community',
        'meta', 'strategy', 'tactics', 'patch', 'update', 'balance',
        'region', 'international', 'global', 'national', 'local', 'venue'
    ]

    message_lower = message.lower()
    
    # Detect date patterns (could indicate tournament scheduling)
    date_pattern = r'\b\d{1,2}[-/\s]?\w+\b'
    if re.search(date_pattern, message_lower):
        return True
        
    # Detect location or time references 
    location_time_keywords = ['where', 'when', 'location', 'place', 'venue', 'time', 'date', 'day', 'schedule', 'on', 'at']
    for word in location_time_keywords:
        if word in message_lower.split():
            return True
    
    # Check for possessive references to tournaments
    possessive_pattern = r'\b(?:my|our|their|your|the)\s+(?:tournament|competition|match|game|event)\b'
    if re.search(possessive_pattern, message_lower):
        return True
    
    # Check for keywords
    for keyword in tournament_keywords:
        if keyword.lower() in message_lower:
            return True

    # Additional heuristic: Check for phrases commonly used in tournament planning
    tournament_phrases = [
        'how to organize', 'best format for', 'rules for', 'how many teams',
        'manage participants', 'schedule matches', 'track scores', 'set up',
        'create a', 'start a', 'run a', 'hosting a', 'how many', 'best way'
    ]

    for phrase in tournament_phrases:
        if phrase.lower() in message_lower:
            return True

    return False

def format_response(response_text):
    """Format the raw LLM response for better presentation"""
    if not response_text:
        return "I apologize, but I couldn't generate a response. Please try again."

    # Remove any unnecessary prefixes
    import re
    clean_response = re.sub(r'^(as an ai assistant|as a tournament planning assistant|i am a tournament planning assistant|as your tournament assistant)', '', response_text, flags=re.IGNORECASE).strip()

    # Ensure first letter is capitalized
    clean_response = clean_response[0].upper() + clean_response[1:] if clean_response else clean_response
    
    # Format response with HTML line breaks and proper styling
    clean_response = format_text_with_html(clean_response)
    
    return clean_response

def format_text_with_html(text):
    """Convert plain text formatting to HTML for better display"""
    if not text:
        return text
        
    # Replace repeated newlines with paragraph breaks
    text = re.sub(r'\n\s*\n', '</p><p>', text)
    
    # Replace single newlines with breaks
    text = text.replace('\n', '<br>')
    
    # Format numbered lists
    text = re.sub(r'(\d+)\.\s+([^\n<]+)', r'<b>\1.</b> \2', text)
    
    # Format bullet points
    text = re.sub(r'[-•*]\s+([^\n<]+)', r'• \1', text)
    
    # Wrap in paragraph if not already
    if not text.startswith('<p>'):
        text = '<p>' + text + '</p>'
        
    # Replace any multiple breaks
    text = re.sub(r'<br>\s*<br>', '</p><p>', text)
    
    # Clean up any empty paragraphs
    text = re.sub(r'<p>\s*</p>', '', text)
    
    return text

def handle_chat_request(message):
    """Process chat request and get response from LLM"""
    try:
        # Include a timestamp in offline responses to make them unique
        timestamp = int(time.time())
        
        # Check if the message is related to tournament planning
        if not is_tournament_related(message):
            return "<p>This query is out of scope. I can only help with tournament planning and management.</p>"
            
        # Add a unique session ID to messages to avoid caching
        user_session_id = request.cookies.get('session_id', str(timestamp))
            
        # Using offline mode (no API calls)
        if USE_OFFLINE_MODE:
            return get_offline_response(message, timestamp)

        # Call the Hugging Face Inference API with a more reliable model
        try:
            input_context = f"""<s>[INST] You are TournamentGenius, a specialized tournament planning assistant. Answer this tournament planning question in comprehensive detail: {message}

Your response should:
1. Include specific examples and clear steps
2. Use HTML formatting (<p>, <ul>, <li>, <b>) for readability
3. Be thorough and informative, at least 150-200 words
4. Include practical advice for tournament organizers
5. Avoid saying "undefined" or giving very short responses
6. Be direct and focused on the tournament planning question

If asked about:
- Tournament formats (explain structures like round robin, single/double elimination)
- Team creation (roster size, roles, management tips)
- Fixtures (provide concrete examples of match schedules)
- Rules and scoring (clear explanation of tournament regulations)
- Venue requirements (equipment, space needs, logistics)

Session ID: {user_session_id}-{timestamp} [/INST]</s>"""
            
            print(f"Calling API for: {message}")
            
            response = requests.post(
                'https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2',
                json={
                    'inputs': input_context,
                    'parameters': {
                        'max_new_tokens': 800,
                        'temperature': 0.7,
                        'top_p': 0.9,
                        'return_full_text': False
                    },
                    'options': {'use_cache': False, 'wait_for_model': True}
                },
                headers={
                    'Authorization': f'Bearer {HUGGINGFACE_API_KEY}',
                    'Content-Type': 'application/json'
                },
                timeout=20  # Increased timeout
            )
            
            print(f"API response status: {response.status_code}")
            
            # Extract and format the response
            if response.status_code == 200:
                try:
                    result = response.json()
                    print(f"Raw API result type: {type(result)}")
                    
                    # Handle different response formats
                    if isinstance(result, list) and len(result) > 0:
                        if 'generated_text' in result[0]:
                            api_response = format_response(result[0]['generated_text'])
                        else:
                            api_response = format_response(str(result[0]))
                    elif isinstance(result, dict) and 'generated_text' in result:
                        api_response = format_response(result['generated_text'])
                    else:
                        api_response = format_response(str(result))
                    
                    # Final validation
                    if api_response and len(api_response) > 50 and 'undefined' not in api_response.lower():
                        return api_response
                    else:
                        print(f"API response too short or contains 'undefined': {api_response}")
                        return get_offline_response(message, timestamp)
                except Exception as e:
                    print(f"Error processing API response: {e}")
                    return get_offline_response(message, timestamp)
            else:
                print(f"API request failed with status {response.status_code}")
                return get_offline_response(message, timestamp)
                
        except requests.exceptions.RequestException as e:
            # If API call fails, use fallback response
            print(f"API request exception: {e}")
            return get_offline_response(message, timestamp)
            
    except Exception as e:
        print(f"Error in chat service: {e}")
        return get_offline_response(message, int(time.time()))

def get_offline_response(message, timestamp=None):
    """Generate an offline response based on message keywords"""
    message_lower = message.lower()
    
    # Add some randomness to responses
    if timestamp is None:
        timestamp = int(time.time())
    
    # Make the response subtly different based on timestamp
    response_variant = timestamp % 3  # Creates 3 variants
    
    # Check for team creation questions
    if any(word in message_lower for word in ['make', 'create', 'form']) and any(word in message_lower for word in ['team', 'squad', 'roster']):
        return """<p>Creating a successful tournament team involves several key steps:</p>
        
        <p><b>Team Formation Essentials:</b></p>
        <ul>
            <li><b>Roster size:</b> Determine optimal team size (core players + substitutes)</li>
            <li><b>Skill balance:</b> Mix experienced players with promising newcomers</li>
            <li><b>Role definition:</b> Clearly establish each player's responsibilities</li>
            <li><b>Team captain:</b> Select a leader for communication and decision-making</li>
            <li><b>Team name/identity:</b> Create a memorable brand for your team</li>
        </ul>
        
        <p><b>Administrative Requirements:</b></p>
        <ul>
            <li><b>Registration forms:</b> Complete all required tournament paperwork</li>
            <li><b>Contact information:</b> Maintain updated contact details for all members</li>
            <li><b>Equipment/uniforms:</b> Ensure consistent appearance if required</li>
            <li><b>Tournament rules:</b> Familiarize all members with competition rules</li>
            <li><b>Practice schedule:</b> Establish regular training sessions before the event</li>
        </ul>
        
        <p><b>Team Management Tips:</b></p>
        <ul>
            <li><b>Communication channel:</b> Create a group chat or email list</li>
            <li><b>Availability tracking:</b> Confirm player availability for all tournament dates</li>
            <li><b>Strategy development:</b> Prepare and practice competitive approaches</li>
            <li><b>Conflict resolution:</b> Establish a process for handling disagreements</li>
            <li><b>Feedback mechanism:</b> Create opportunities for constructive criticism</li>
        </ul>
        
        <p>Would you like more specific advice on any aspect of team creation?</p>"""
    
    # Check for 16-team fixture/schedule questions
    if any(word in message_lower for word in ['fixture', 'schedule', 'bracket', 'draw']) and ('16' in message_lower or 'sixteen' in message_lower):
        return """<p>For a 16-team tournament, here are the most common format options with their fixture structures:</p>
        
        <p><b>1. Single Elimination Bracket (15 matches total)</b></p>
        <ul>
            <li><b>Round 1 (Round of 16):</b> 8 matches - Teams 1v16, 8v9, 5v12, 4v13, 3v14, 6v11, 7v10, 2v15</li>
            <li><b>Quarterfinals:</b> 4 matches - Winners of Round 1 matches</li>
            <li><b>Semifinals:</b> 2 matches - Winners of Quarterfinals</li>
            <li><b>Final:</b> 1 match - Winners of Semifinals</li>
        </ul>
        
        <p><b>2. Double Elimination (30 matches maximum)</b></p>
        <ul>
            <li>Follows single elimination format but with a losers bracket</li>
            <li>Teams need to lose twice to be eliminated</li>
            <li>Requires approximately twice the number of matches</li>
        </ul>
        
        <p><b>3. Group Stage + Knockout (32 matches total)</b></p>
        <ul>
            <li><b>Group Stage:</b> 4 groups of 4 teams each (6 matches per group, 24 total)</li>
            <li><b>Each team plays 3 matches</b> (once against each team in their group)</li>
            <li><b>Quarterfinals:</b> Top 2 teams from each group advance (4 matches)</li>
            <li><b>Semifinals:</b> 2 matches</li>
            <li><b>Final & 3rd place match:</b> 2 matches</li>
        </ul>
        
        <p><b>4. Swiss System (5-7 rounds, 40-56 matches total)</b></p>
        <ul>
            <li>Each round pairs teams with similar records</li>
            <li>No eliminations until final standings</li>
            <li>Recommended for 5-7 rounds for 16 teams</li>
            <li>8 matches per round (40-56 matches total)</li>
        </ul>
        
        <p>For creating the actual fixture schedule, I recommend using tournament software like Challonge, Toornament, or dedicated spreadsheet templates that can generate the matchups automatically based on your chosen format.</p>"""
    
    # Check for chess tournament equipment questions
    if any(word in message_lower for word in ['chess', 'equipment', 'supplies', 'need']) and any(word in message_lower for word in ['tournament', 'competition', 'event']):
        return """<p>For organizing a chess tournament, you'll need the following equipment:</p>
        
        <p><b>Essential Chess Equipment:</b></p>
        <ul>
            <li><b>Chess sets:</b> Standard Staunton design, with 3.75" king height for tournament play</li>
            <li><b>Chess boards:</b> Standard 2.25" squares, vinyl rollup mats are cost-effective</li>
            <li><b>Chess clocks:</b> Digital preferred (DGT, Chronos) with delay/increment capability</li>
            <li><b>Score sheets:</b> Standard algebraic notation sheets for players to record moves</li>
            <li><b>Pens:</b> Provide for players to fill in score sheets</li>
        </ul>
        
        <p><b>Tournament Organization Materials:</b></p>
        <ul>
            <li><b>Pairing software:</b> Swiss-Manager, Vega, or lichess.org's free tournament manager</li>
            <li><b>Results slips:</b> For players to record and submit game outcomes</li>
            <li><b>Wall charts/projector:</b> To display standings and pairings</li>
            <li><b>Table numbers:</b> To help players find their boards</li>
            <li><b>Rule books:</b> FIDE/National Chess Federation rules as appropriate</li>
        </ul>
        
        <p><b>Venue Requirements:</b></p>
        <ul>
            <li><b>Tables:</b> At least 2.5' x 2.5' per board</li>
            <li><b>Chairs:</b> Comfortable enough for long games</li>
            <li><b>Good lighting:</b> Critical for players to see the board clearly</li>
            <li><b>Quiet environment:</b> Minimize external noise</li>
            <li><b>Tournament director's table:</b> Central location for administration</li>
        </ul>
        
        <p><b>Optional/Additional Items:</b></p>
        <ul>
            <li><b>Spare pieces and boards:</b> In case of damage or loss</li>
            <li><b>Demonstration board:</b> For game analysis or featured matches</li>
            <li><b>Certificates/trophies:</b> For winners and participants</li>
            <li><b>Name tags:</b> For officials and staff</li>
            <li><b>First aid kit:</b> For any minor emergencies</li>
        </ul>
        
        <p>For large tournaments, consider renting equipment from local chess clubs or federations to reduce costs.</p>"""
    
    # Round-robin tournament organization
    if ('round' in message_lower and 'robin' in message_lower) or 'round-robin' in message_lower:
        if any(word in message_lower for word in ['organize', 'create', 'start', 'setup', 'schedule', 'plan']):
            return """<p>Organizing a round-robin tournament requires careful planning. Here's a comprehensive guide:</p>

            <p><b>1. Planning Your Round-Robin Tournament</b></p>
            <ul>
                <li><b>Determine participant count:</b> Ideal for 6-12 teams (more teams require more rounds)</li>
                <li><b>Calculate total matches:</b> n(n-1)/2 where n = number of teams</li>
                <li><b>Assess time constraints:</b> Each team plays (n-1) matches</li>
                <li><b>Venue requirements:</b> Ensure adequate space and time allocation</li>
            </ul>

            <p><b>2. Creating the Schedule (Circle Method)</b></p>
            <ol>
                <li>Assign numbers to each team (1 through n)</li>
                <li>If you have an odd number of teams, add a "bye" (making it even)</li>
                <li>Place team #1 at the top and arrange remaining teams in a circle</li>
                <li>Record the matchups for round 1 (each team paired with the one opposite)</li>
                <li>Rotate all teams except #1 clockwise for the next round</li>
                <li>Repeat until all rounds are scheduled</li>
            </ol>

            <p><b>3. Schedule Example for 8 Teams</b></p>
            <p>Round 1: 1v8, 2v7, 3v6, 4v5<br>
            Round 2: 1v7, 8v6, 2v5, 3v4<br>
            Round 3: 1v6, 7v5, 8v4, 2v3<br>
            Round 4: 1v5, 6v4, 7v3, 8v2<br>
            Round 5: 1v4, 5v3, 6v2, 7v8<br>
            Round 6: 1v3, 4v2, 5v8, 6v7<br>
            Round 7: 1v2, 3v8, 4v7, 5v6</p>

            <p><b>4. Logistical Considerations</b></p>
            <ul>
                <li><b>Home/away balance:</b> Alternate if applicable</li>
                <li><b>Rest periods:</b> Avoid scheduling teams for consecutive matches</li>
                <li><b>Field/court rotation:</b> Distribute premium playing areas fairly</li>
                <li><b>Time slots:</b> Account for match duration, setup, and breakdown time</li>
            </ul>

            <p><b>5. Tournament Management</b></p>
            <ul>
                <li><b>Scoring system:</b> Define points for wins, draws, losses (e.g., 3-1-0)</li>
                <li><b>Tiebreakers:</b> Establish clear criteria (head-to-head, point differential, etc.)</li>
                <li><b>Results tracking:</b> Update standings after each match</li>
                <li><b>Software tools:</b> Consider using Tournament.io, Challonge, or Excel templates</li>
            </ul>

            <p><b>6. Communication</b></p>
            <ul>
                <li>Distribute complete schedule to all teams before the tournament</li>
                <li>Provide regular standings updates throughout the event</li>
                <li>Clearly communicate tiebreaker rules in advance</li>
            </ul>

            <p>Would you like me to elaborate on any specific aspect of round-robin tournament organization?</p>"""
    
    # Check for fixture related questions
    if any(word in message_lower for word in ['fixture', 'schedule', 'pairing', 'matchup']) or 'how' in message_lower and any(word in message_lower for word in ['create', 'make', 'generate', 'set up']):
        if '12' in message_lower or 'twelve' in message_lower:
            return """<p>For creating fixtures for a 12-team tournament, you have several options:</p>
            
            <p><b>1. Round Robin Format</b></p>
            <p>For a complete round robin where all teams play each other once:</p>
            <ul>
                <li>Each team will play 11 matches (playing every other team once)</li>
                <li>Total matches: 66 (12 × 11 ÷ 2)</li>
                <li>Typically requires 11 rounds to complete</li>
            </ul>
            
            <p><b>2. Groups + Knockout Format</b></p>
            <p>Split into 4 groups of 3 teams each:</p>
            <ul>
                <li>Group stage: Each team plays 2 matches (3 matches per group, 12 total)</li>
                <li>Top 2 from each group advance to quarterfinals (8 teams)</li>
                <li>Then 4 quarterfinals, 2 semifinals, and 1 final</li>
                <li>Total matches: 12 (group) + a (quarterfinals) + 2 (semifinals) + 1 (final) = 19 matches</li>
            </ul>
            
            <p><b>3. Swiss System (5 rounds)</b></p>
            <ul>
                <li>Round 1: Random or seeded pairings</li>
                <li>Rounds 2-5: Teams with similar records play each other</li>
                <li>Total matches: 30 (6 matches per round × 5 rounds)</li>
                <li>At the end, rank teams by their record or use tiebreakers</li>
            </ul>
            
            <p>To create the actual fixture table, use tournament software like:</p>
            <ul>
                <li><b>Challonge:</b> Free online bracket generator with round robin support</li>
                <li><b>Toornament:</b> Offers templates for various formats</li>
                <li><b>Microsoft Excel:</b> Use templates or create manually with formulas</li>
            </ul>
            
            <p>For your 12-team tournament, I recommend the Groups + Knockout format unless you have plenty of time for a full round robin.</p>"""
        else:
            return """<p>Creating fixtures (match schedules) depends on your tournament format and number of teams. Here are the main approaches:</p>
            
            <p><b>1. Round Robin Format</b></p>
            <ul>
                <li>Each team plays against all other teams once (or twice for double round robin)</li>
                <li>For n teams, each team plays (n-1) matches</li>
                <li>Total matches = n × (n-1) ÷ 2</li>
                <li>Use the "circle method" where one team stays fixed while others rotate</li>
            </ul>
            
            <p><b>2. Elimination Brackets</b></p>
            <ul>
                <li><b>Single elimination:</b> Losers are immediately eliminated</li>
                <li><b>Double elimination:</b> Losers move to a losers bracket</li>
                <li>For n teams, you'll have (n-1) matches in single elimination</li>
                <li>Seed teams appropriately to balance the bracket</li>
            </ul>
            
            <p><b>3. Groups + Knockout</b></p>
            <ul>
                <li>Divide teams into equal groups for round robin play</li>
                <li>Top teams from each group advance to elimination rounds</li>
                <li>Example: 4 groups of 4, top 2 from each advance to quarterfinals</li>
            </ul>
            
            <p><b>4. Swiss System</b></p>
            <ul>
                <li>Teams with similar records play each other in each round</li>
                <li>No eliminations until the final standings</li>
                <li>Good for large fields where full round robin isn't feasible</li>
            </ul>
            
            <p>To create actual fixtures, you can use software like:</p>
            <ul>
                <li><b>Challonge:</b> Free online bracket generator</li>
                <li><b>Toornament:</b> Robust tournament management platform</li>
                <li><b>Battlefy:</b> Popular for esports tournaments</li>
            </ul>
            
            <p>How many teams are in your tournament? I can provide more specific guidance based on your number of participants.</p>"""
    
    # Check for greetings
    greeting_pattern = r'\b(?:hi|hello|hey|greetings|howdy)\b'
    if re.search(greeting_pattern, message_lower) and len(message_lower) < 10:
        greetings = [
            "<p>Hello! I'm your tournament planning assistant. How can I help you organize a tournament today?</p>",
            "<p>Hi there! Ready to help with your tournament planning needs. What would you like assistance with?</p>",
            "<p>Hey! I'm here to help with your tournament organization. What aspect are you working on?</p>"
        ]
        return greetings[response_variant]
    
    # Check for specific date mentions
    date_match = re.search(r'\b(\d{1,2})\s?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b', message_lower)
    if date_match:
        return f"<p>I see your tournament is planned for {date_match.group(0)}. Make sure to send out invitations at least 3-4 weeks in advance, confirm your venue, and prepare your schedule and bracket templates.</p>"
    
    # Check for questions about tournament size
    size_pattern = r'\b(?:how many|number of)\s+(?:teams|players|participants|people)\b'
    if re.search(size_pattern, message_lower):
        return """<p>The ideal number of participants depends on your format:</p>
        
        <p>• For single elimination: Powers of 2 (8, 16, 32, 64) work best</p>
        <p>• For double elimination: Same as single, but plan for about 1.5x more matches</p>
        <p>• For round robin: Usually best with 6-10 participants (otherwise too many matches)</p>
        <p>• For Swiss: Works with any number, but 8+ is better</p>
        
        <p>With more participants, consider using qualifying rounds or group stages.</p>"""
    
    # Questions about scheduling
    if any(word in message_lower for word in ['schedule', 'when', 'time', 'date', 'how long']):
        return """<p>For tournament scheduling, consider:</p>
        
        <p><b>1.</b> Match duration: Estimate realistic times including setup/teardown</p>
        <p><b>2.</b> Breaks: Allow 10-15 minutes between matches and longer breaks for meals</p>
        <p><b>3.</b> Concurrent matches: If possible, run multiple matches simultaneously</p>
        <p><b>4.</b> Buffer time: Add 15-20% extra time for delays</p>
        <p><b>5.</b> Player fatigue: Avoid scheduling too many consecutive matches for same team</p>
        
        <p>Create a detailed schedule and share it with all participants in advance.</p>"""
        
    # Questions about team/player management
    if any(word in message_lower for word in ['teams', 'players', 'participants', 'registration', 'sign up', 'join']):
        return """<p>For managing tournament participants:</p>
        
        <p><b>1.</b> Registration: Use a form with team name, captain contact, roster, and skill level</p>
        <p><b>2.</b> Seeding: Rank teams based on previous performance if available</p>
        <p><b>3.</b> Check-in: Require teams to check in 30-60 minutes before their first match</p>
        <p><b>4.</b> Rules briefing: Hold a captains' meeting to review rules</p>
        <p><b>5.</b> Communication: Create a centralized way to announce updates (app, website, etc.)</p>
        
        <p>Clear organization of participants is key to a smooth tournament.</p>"""
        
    # Questions about tournament rules
    if any(word in message_lower for word in ['rules', 'scoring', 'points', 'win', 'lose', 'regulations']):
        return """<p>When establishing tournament rules:</p>
        
        <p><b>1.</b> Game-specific rules: Clearly define any modifications to standard game rules</p>
        <p><b>2.</b> Match format: Specify number of games/sets/rounds per match</p>
        <p><b>3.</b> Scoring system: Define how winners are determined and points awarded</p>
        <p><b>4.</b> Tiebreakers: Establish criteria for resolving ties in standings</p>
        <p><b>5.</b> Conduct rules: Set expectations for sportsmanship and penalties for violations</p>
        
        <p>Document all rules and distribute to participants before the tournament begins.</p>"""
    
    # Questions about brackets and advancement
    if any(word in message_lower for word in ['bracket', 'elimination', 'knockout', 'advance', 'progress', 'move on']):
        return """<p>For tournament advancement and brackets:</p>
        
        <p><b>1.</b> Single elimination: Winners advance, losers are eliminated</p>
        <p><b>2.</b> Double elimination: Players move to losers bracket after first loss, eliminated after second</p>
        <p><b>3.</b> Group stage: Top 1-2 teams from each group advance to playoffs</p>
        <p><b>4.</b> Swiss system: Players with similar records are paired, final rankings determine winners</p>
        
        <p>Use tournament software or websites like Challonge or Toornament to create and manage your brackets.</p>"""
        
    # Questions about venues and equipment
    if any(word in message_lower for word in ['venue', 'location', 'place', 'equipment', 'setup', 'space']):
        return """<p>When selecting a tournament venue:</p>
        
        <p><b>1.</b> Size: Ensure adequate space for all matches, participants, and spectators</p>
        <p><b>2.</b> Equipment: Confirm all necessary game equipment, tables, chairs, etc.</p>
        <p><b>3.</b> Technical needs: Check power outlets, internet connectivity, A/V systems</p>
        <p><b>4.</b> Amenities: Consider restrooms, food/drink options, parking availability</p>
        <p><b>5.</b> Cost: Factor in rental fees, insurance, and security deposits</p>
        
        <p>Visit potential venues in person before booking to verify suitability.</p>"""
        
    # Questions about prizes and rewards
    if any(word in message_lower for word in ['prize', 'reward', 'winning', 'trophy', 'money']):
        return """<p>For tournament prizes and rewards:</p>
        
        <p><b>1.</b> Budget appropriately: Typically 50-70% of entry fees go to prize pool</p>
        <p><b>2.</b> Distribution: Common splits are 60/30/10 for 1st/2nd/3rd places</p>
        <p><b>3.</b> Trophy options: Physical trophies, medals, certificates, or digital badges</p>
        <p><b>4.</b> Sponsor prizes: Consider product donations from relevant sponsors</p>
        <p><b>5.</b> Recognition: Plan for awards ceremony and winner announcements</p>
        
        <p>Clearly communicate prize structure to participants before registration.</p>"""
        
    # Questions about promotion and marketing
    if any(word in message_lower for word in ['promote', 'marketing', 'advertise', 'announcement', 'invite']):
        return """<p>To promote your tournament effectively:</p>
        
        <p><b>1.</b> Create event pages on social media and gaming platforms</p>
        <p><b>2.</b> Design eye-catching graphics with key details (date, location, prizes)</p>
        <p><b>3.</b> Contact relevant communities, clubs, and organizations</p>
        <p><b>4.</b> Consider early-bird registration discounts to build momentum</p>
        <p><b>5.</b> Partner with sponsors for cross-promotion opportunities</p>
        
        <p>Start promotion at least 1-2 months before registration deadline.</p>"""
        
    # Default fallback - don't use this for every question
    # First check if message contains any tournament-related keywords
    if any(word in message_lower for word in tournament_keywords):
        responses = [
            """<p>To help you with this tournament planning question, I need a bit more information. Could you specify what aspect you're looking for help with? For example:</p>
            <ul>
                <li>Tournament format selection</li>
                <li>Schedule creation</li>
                <li>Participant management</li>
                <li>Rules and scoring</li>
                <li>Venue requirements</li>
            </ul>""",
            
            """<p>I'd be happy to assist with your tournament planning question. To provide the most relevant advice, could you elaborate on:</p>
            <ul>
                <li>What type of game/sport is the tournament for?</li>
                <li>How many participants do you expect?</li>
                <li>What's your timeline for the event?</li>
            </ul>""",
            
            """<p>For this tournament planning question, I can provide more specific guidance if you let me know:</p>
            <ul>
                <li>Your tournament goals (competitive, casual, charity, etc.)</li>
                <li>Any specific challenges you're facing</li>
                <li>Your experience level with organizing tournaments</li>
            </ul>"""
        ]
        return responses[response_variant]
        
    # If nothing else matches, use the general response
    return """<p>For successful tournament planning, focus on these key areas:</p>
    
    <p><b>1.</b> Format: Choose the right tournament structure for your number of participants and time constraints</p>
    <p><b>2.</b> Scheduling: Create a realistic timeline with buffer for delays</p>
    <p><b>3.</b> Participants: Organize registration, seeding, and check-in processes</p>
    <p><b>4.</b> Venue: Secure an appropriate location with necessary facilities</p>
    <p><b>5.</b> Rules: Clearly define and communicate all tournament regulations</p>
    <p><b>6.</b> Communication: Keep participants informed before and during the event</p>
    
    <p>What specific aspect of tournament planning can I help you with today?</p>"""

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('public', 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """API endpoint for chat interactions"""
    try:
        data = request.json
        message = data.get('message', '')
        response = handle_chat_request(message)
        return jsonify({"response": response})
    except Exception as e:
        print(f"Error processing chat request: {e}")
        return jsonify({"error": "An error occurred while processing your request"}), 500

if __name__ == '__main__':
    print(f"Tournament Planner Bot server running on port {PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)