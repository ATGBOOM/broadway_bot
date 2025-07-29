# Broadway Fashion Bot

An AI-powered fashion chatbot that provides personalized styling advice, outfit recommendations, and fashion guidance through an interactive chat interface.

## Features

- **Occasion-based styling**: Get outfit recommendations for specific events (weddings, interviews, dates, etc.)
- **Vacation wardrobe planning**: Pack the perfect outfits based on your destination and activities
- **Style pairing advice**: Learn what goes well with items you already own
- **Personal styling**: Get advice on colors and styles that suit you
- **Outfit rating**: Upload photos and get feedback on your look
- **Real-time chat interface**: Interactive web-based chat with image upload support

## Tech Stack

- **Backend**: FastAPI with WebSocket support
- **AI**: OpenAI GPT models with LangGraph for conversation flow
- **Database**: PostgreSQL with JSON fallback
- **Frontend**: HTML/CSS/JavaScript chat interface
- **Image Processing**: PIL (Pillow) for image handling

## Quick Start

1. **Clone the repository**
```bash
git clone <your-repo-url>
cd broadway-fashion-bot
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**
```bash
# Create .env file
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=your_postgresql_url_here  # Optional - will use JSON fallback if not provided
```

4. **Run the application**
```bash
python main.py
```

5. **Open your browser**
Navigate to `http://localhost:8000` to start chatting with the fashion bot!

## Usage

The bot offers 5 main services:

1. **Occasion Styling** - "I have a wedding to attend next month"
2. **Vacation Planning** - "I'm going to Paris for a week in summer"  
3. **Style Pairing** - "What goes well with my black leather jacket?"
4. **Personal Styling** - "Would green jackets look good on me?"
5. **Outfit Rating** - Upload a photo and type "Rate my OTD"

Simply start typing your fashion questions or click the service buttons to get started!

## Deployment

The app is configured for easy deployment on platforms like Heroku:

- Uses environment variables for configuration
- Automatic port detection from `PORT` environment variable
- PostgreSQL support with JSON fallback for development

## API Endpoints

- `/` - Chat interface
- `/feedback` - View user feedback data
- `/feedback/stats` - Feedback statistics
- `/db-status` - Database connection status

## Contributing

Feel free to submit issues and enhancement requests!