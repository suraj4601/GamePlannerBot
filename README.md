# TournamentGenius

A specialized chatbot designed to help users plan and manage game tournaments. This chatbot uses Hugging Face's free API to provide domain-specific responses to tournament-related queries.

![TournamentGenius Screenshot](gameplanerbot\public\images\screnshot.jpg)

## Features

- Beautiful, modern UI with animated components
- Domain-specific responses for tournament planning and management
- Support for various tournament formats and scheduling options
- Participant management guidance
- Game-specific tournament rules information
- Out-of-scope detection for non-tournament-related queries
- **Free API Usage**: Uses Hugging Face's Inference API with free tier access

## Setup

1. Clone this repository
2. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory with your Hugging Face API key:
   ```
   PORT=3000
   HUGGINGFACE_API_KEY=your_huggingface_api_key_here
   ```
   Note: You can get a free API key by creating an account at [Hugging Face](https://huggingface.co)
   
4. Start the server:
   ```
   python app.py
   ```

## Usage

Once the server is running, open your browser and navigate to `http://localhost:3000`. You can interact with the chatbot through the web interface.

Example queries:
- "What tournament format is best for 16 teams?"
- "How do I organize a double elimination bracket?"
- "How many matches would I need for a round-robin tournament with 8 teams?"
- "What's the best way to seed players in a knockout tournament?"

## Architecture

- **Frontend**: Modern HTML/CSS/JS interface with animations
- **Backend**: Flask server handling requests to the Hugging Face API
- **Domain Scope**: Specialized for tournament planning and management

## Technologies Used

- Python with Flask
- Hugging Face Inference API (Free Tier)
- Modern HTML5, CSS3, and JavaScript
- Font Awesome for icons

## Screenshots

Coming soon! 