import io
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
import os
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import asyncpg
from PIL import Image
# Your existing imports
from occasionService import OccasionService
from reccomendationBot import RecommendationService
from pairingService import PairingService
from vacationService import VacationService  
from conversationService import ConversationService
from generalService import GeneralService
from genderService import GenderService
from looksGoodOnMeService import LooksGoodOnMeService
# NEW: Import LangGraph integration
from fashion_graph import ChatSession

app = FastAPI(title="Broadway Fashion Bot WebSocket")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL")

# JSON fallback setup
FEEDBACK_FILE = "feedback.json"

def load_feedback():
    """Load existing feedback from JSON file (fallback)"""
    if Path(FEEDBACK_FILE).exists():
        try:
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading feedback file: {e}")
            return []
    return []

def save_feedback_to_file(feedback_list):
    """Save feedback list to JSON file (fallback)"""
    try:
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(feedback_list, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving feedback file: {e}")

# Load existing feedback on startup (fallback)
feedback_data = load_feedback()

async def init_postgres():
    """Initialize PostgreSQL connection and tables"""
    if not DATABASE_URL:
        print("❌ No DATABASE_URL found. Using JSON fallback.")
        return False
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        # Create feedback table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id SERIAL PRIMARY KEY,
                client_id TEXT NOT NULL,
                user_input TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                bot_intent TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.close()
        print("✅ PostgreSQL feedback table initialized")
        return True
    except Exception as e:
        print(f"❌ Error initializing PostgreSQL: {e}")
        return False

async def save_feedback_postgres(client_id: str, user_input: str, bot_response: str, bot_intent: str, feedback_type: str):
    """Save feedback to PostgreSQL"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        await conn.execute('''
            INSERT INTO feedback (client_id, user_input, bot_response, bot_intent, feedback_type)
            VALUES ($1, $2, $3, $4, $5)
        ''', client_id, user_input, bot_response, bot_intent, feedback_type)
        
        await conn.close()
        print(f"✅ Feedback saved to PostgreSQL: {feedback_type} for client {client_id}, intent: {bot_intent}")
        return True
    except Exception as e:
        print(f"❌ Error saving to PostgreSQL: {e}")
        return False

async def get_feedback_postgres():
    """Get all feedback from PostgreSQL"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        rows = await conn.fetch('''
            SELECT id, client_id, user_input, bot_response, bot_intent, feedback_type, timestamp
            FROM feedback
            ORDER BY timestamp DESC
        ''')
        
        await conn.close()
        
        feedback_list = []
        for row in rows:
            feedback_list.append({
                "id": row['id'],
                "client_id": row['client_id'],
                "user_input": row['user_input'],
                "bot_response": row['bot_response'],
                "bot_intent": row['bot_intent'],
                "feedback_type": row['feedback_type'],
                "timestamp": row['timestamp'].isoformat()
            })
        
        return feedback_list
    except Exception as e:
        print(f"❌ Error getting feedback from PostgreSQL: {e}")
        return []

async def get_feedback_stats_postgres():
    """Get feedback statistics from PostgreSQL"""
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        
        rows = await conn.fetch('''
            SELECT feedback_type, COUNT(*) as count
            FROM feedback
            GROUP BY feedback_type
        ''')
        
        await conn.close()
        
        stats = {}
        for row in rows:
            stats[row['feedback_type']] = row['count']
        
        return stats
    except Exception as e:
        print(f"❌ Error getting stats from PostgreSQL: {e}")
        return {}

async def save_feedback(client_id: str, user_input: str, bot_response: str, bot_intent: str, feedback_type: str):
    """Save feedback - try PostgreSQL first, fallback to JSON"""
    
    # Try PostgreSQL first
    if DATABASE_URL:
        success = await save_feedback_postgres(client_id, user_input, bot_response, bot_intent, feedback_type)
        if success:
            return
    
    # Fallback to JSON file
    try:
        global feedback_data
        
        new_feedback = {
            "id": len(feedback_data) + 1,
            "client_id": client_id,
            "user_input": user_input,
            "bot_response": bot_response,
            "bot_intent": bot_intent,
            "feedback_type": feedback_type,
            "timestamp": datetime.now().isoformat()
        }
        
        feedback_data.append(new_feedback)
        save_feedback_to_file(feedback_data)
        
        print(f"✅ Feedback saved to JSON: {feedback_type} for client {client_id}, intent: {bot_intent}")
    except Exception as e:
        print(f"❌ Error saving feedback: {e}")

# Initialize on startup
@app.on_event("startup")
async def startup():
    if DATABASE_URL:
        await init_postgres()
        print("✅ Using PostgreSQL for feedback storage")
    else:
        print("ℹ️ Using JSON file for feedback storage")

# Your existing service initialization
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ OPENAI_API_KEY environment variable not set!")
else:
    print("✅ OPENAI_API_KEY found in environment")

# Initialize services
try:
    occasion_service = OccasionService()
    recommendation_service = RecommendationService()
    pairing_service = PairingService()
    vacation_service = VacationService()
    general_service = GeneralService()
    styling_service = LooksGoodOnMeService()
    print("✅ Services initialized successfully")
except Exception as e:
    print(f"❌ Error initializing services: {e}")
    raise

# Store active chat sessions and conversation history
chat_sessions: Dict[str, ChatSession] = {}
conversation_history: Dict[str, list] = {}
user_states: Dict[str, str] = {}  # Track user's current state

# Service examples mapping
SERVICE_EXAMPLES = {
    "1": {
        "name": "Occasion Service",
        "description": "Get outfit recommendations for specific events and occasions",
        "examples": [
            "I have a wedding to attend next month",
            "What should I wear to a job interview?",
            "I need an outfit for a dinner date",
            "Help me dress for a business meeting",
            "What's appropriate for a casual brunch?"
        ]
    },
    "2": {
        "name": "Vacation Service", 
        "description": "Plan your travel wardrobe based on destination and activities",
        "examples": [
            "I'm going to Paris for a week in summer",
            "Planning a beach vacation in Goa",
            "What to pack for a ski trip to Switzerland?",
            "Business trip to New York in winter",
            "Backpacking through Southeast Asia"
        ]
    },
    "3": {
        "name": "Pairing Service",
        "description": "Get suggestions on what goes well with items you already own",
        "examples": [
            "What goes well with my black leather jacket?",
            "I have a red dress, what shoes should I wear?",
            "How can I style my white sneakers?",
            "What bottoms go with this striped top?",
            "Accessories to pair with my navy blazer?"
        ]
    },
    "4": {
        "name": "Styling Service",
        "description": "Personal styling advice based on your preferences and body type",
        "examples": [
            "Would green jackets look good on me?",
            "what color dresses would look good on me?",
            "Would a red dress look good on me?",
        ]
    }
}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    # Initialize services dict for LangGraph
    services_dict = {
        'occasion': OccasionService(),
        'recommendation': RecommendationService(),
        'pairing': PairingService(),
        'vacation': VacationService(),
        'conversation': ConversationService(),
        'general': GeneralService(),
        'gender' : GenderService(),
        'styling' : LooksGoodOnMeService()
    }
    
    if client_id not in chat_sessions:
        chat_sessions[client_id] = ChatSession(services_dict)
        chat_sessions[client_id].client_id = client_id
        conversation_history[client_id] = []
        user_states[client_id] = "menu"  # Start with menu state
    
    session = chat_sessions[client_id]
    
    # Send initial menu message with interactive buttons
    initial_message = """👋 Welcome to Broadway Fashion! I'm here to help you find the perfect outfit.

Please choose which service you'd like to try, or just start chatting about what you need help with:"""
    
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": initial_message,
        "timestamp": asyncio.get_event_loop().time(),
        "message_id": f"bot_{len(conversation_history[client_id])}",
        "show_service_buttons": True,
        "services": SERVICE_EXAMPLES
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            print("message received =", message_data)
            image = None
            if 'image' in message_data and message_data['image']:
                # Convert base64 to PIL Image
                import base64
                base64_string = message_data['image']
                if base64_string.startswith('data:image'):
                    base64_string = base64_string.split(',')[1]
                
                image_bytes = base64.b64decode(base64_string)
                image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            if message_data.get("type") == "feedback":
                message_id = message_data.get("message_id")
                feedback_type = message_data.get("feedback")  # "thumbs_up" or "thumbs_down"
                
                # Find the conversation pair
                history = conversation_history[client_id]
                for i, entry in enumerate(history):
                    if entry.get("bot_message_id") == message_id:
                        await save_feedback(
                            client_id=client_id,
                            user_input=entry.get("user_input", ""),
                            bot_response=entry.get("bot_response", ""),
                            bot_intent=entry.get("bot_intent", "unknown"),
                            feedback_type=feedback_type
                        )
                        
                        # Send confirmation
                        await websocket.send_text(json.dumps({
                            "type": "feedback_confirmation",
                            "message": "Thank you for your feedback!" if feedback_type == "thumbs_up" else "Thank you for your feedback. We'll work to improve!",
                            "message_id": message_id
                        }))
                        break
                continue
            # Handle followup responses
            if message_data.get("type") == "followup_response":
                followup_responses = message_data.get("responses", {})
                

                #previous_query = session.last_user_query or ""
                query = f"Info provided for the following - {followup_responses.keys()}"
                print("query is", query)
                # Process with the previous query and new followup data
                messages = await session.process_with_langgraph(
                    user_input=query,  
                    client_id=client_id,
                    followup_data=followup_responses 
                )
                
                # Send the response messages
                for message in messages:
                    if message.get("type") == "bot_message":
                        bot_response = message.get("message", "")
                        message_id = f"bot_{len(conversation_history[client_id])}"
                        message["message_id"] = message_id
                        message["show_feedback"] = True
                    elif message.get("type") == "intent":
                        bot_intent = message.get("message", "unknown")
                        await websocket.send_text(json.dumps(message))
                        continue
                    elif message.get("type") == "followup":
                        print("followup message in frontend", message)
                        pass
                    await websocket.send_text(json.dumps(message))
                
                # # Store in conversation history
                # conversation_history[client_id].append({
                #     "user_input": f"Followup for: {previous_query}",
                #     "bot_response": bot_response,
                #     "bot_intent": bot_intent,
                #     "bot_message_id": message_id,
                #     "timestamp": datetime.now().isoformat()
                # })
                continue
            # Handle service button clicks
            if message_data.get("type") == "service_button":
                service_key = message_data.get("service")
                await handle_service_button_click(websocket, service_key, client_id)
                continue
            
            user_input = message_data.get("message", "").strip()
            
            if not user_input:
                continue
            
            # Echo user message
            await websocket.send_text(json.dumps({
                "type": "user_message", 
                "message": user_input,
                "timestamp": asyncio.get_event_loop().time()
            }))
            image = None
            if 'image' in message_data.keys():
                image = message_data.get('image')
            # Handle user input based on current state
            await handle_user_input_with_state(websocket, session, user_input, client_id, image)
            
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        if client_id in chat_sessions:
            del chat_sessions[client_id]
        if client_id in conversation_history:
            del conversation_history[client_id]
        if client_id in user_states:
            del user_states[client_id]
    except Exception as e:
        print(f"WebSocket error: {e}")

async def handle_service_button_click(websocket: WebSocket, service_key: str, client_id: str):
    """Handle when user clicks a service button"""
    
    if service_key not in SERVICE_EXAMPLES:
        return
    
    service_info = SERVICE_EXAMPLES[service_key]
    user_states[client_id] = "chat"  # Switch to chat state
    
    # Send service selection message
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": f"Great! You've selected the **{service_info['name']}** ✨",
        "timestamp": asyncio.get_event_loop().time(),
        "message_id": f"bot_{len(conversation_history[client_id])}"
    }))
    
    # Send service examples
    await websocket.send_text(json.dumps({
        "type": "service_examples",
        "service_name": service_info['name'],
        "description": service_info['description'],
        "examples": service_info['examples'],
        "timestamp": asyncio.get_event_loop().time()
    }))
    
    # Send follow-up message
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": "What would you like help with? You can try one of the examples above or describe your specific needs!",
        "timestamp": asyncio.get_event_loop().time(),
        "message_id": f"bot_{len(conversation_history[client_id])}_followup",
        "show_feedback": True
    }))

async def handle_user_input_with_state(websocket: WebSocket, session: ChatSession, user_input: str, client_id: str, image):
    """Handle user input based on current state (menu vs normal chat)"""
    
    current_state = user_states.get(client_id, "menu")
    
    # If user is in menu state, check for service selection
    if current_state == "menu":
        if user_input in ["1", "2", "3", "4"]:
            await handle_service_selection(websocket, user_input, client_id)
            return
        elif user_input.lower() in ["menu", "back", "main menu", "start over"]:
            await show_main_menu(websocket, client_id)
            return
        else:
            # User didn't select a service but wants to chat normally
            # Switch to chat mode and process their input
            user_states[client_id] = "chat"
            await process_user_input_new(websocket, session, user_input, client_id, image)
            return
    
    # Handle special commands in any state
    if user_input.lower() in ["menu", "back", "main menu", "start over"]:
        await show_main_menu(websocket, client_id)
        return
    
    # Normal chat processing
    await process_user_input_new(websocket, session, user_input, client_id, image)

async def show_main_menu(websocket: WebSocket, client_id: str):
    """Show the main service selection menu"""
    user_states[client_id] = "menu"
    
    menu_message = """🏠 **Main Menu** - Choose a service to try, or just start chatting:"""
    
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": menu_message,
        "timestamp": asyncio.get_event_loop().time(),
        "message_id": f"bot_{len(conversation_history[client_id])}",
        "show_service_buttons": True,
        "services": SERVICE_EXAMPLES
    }))

async def handle_service_selection(websocket: WebSocket, selection: str, client_id: str):
    """Handle when user selects a service by typing 1-4"""
    
    service_info = SERVICE_EXAMPLES[selection]
    user_states[client_id] = "chat"  # Switch to chat state
    
    examples_text = "\n".join([f"• {example}" for example in service_info["examples"]])
    
    response_message = f"""Great choice! You've selected the **{service_info['name']}** ✨

{service_info['description']}

Here are some example prompts you can try:

{examples_text}

You can also ask me anything related to this service, or type **'menu'** anytime to return to the main menu.

What would you like help with?"""
    
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": response_message,
        "timestamp": asyncio.get_event_loop().time(),
        "message_id": f"bot_{len(conversation_history[client_id])}",
        "show_feedback": True
    }))
    
async def process_user_input_new(websocket: WebSocket, session: ChatSession, user_input: str, client_id: str, image):
    """New process function using LangGraph"""
    
    try:
        # Show typing indicator
        await websocket.send_text(json.dumps({
            "type": "typing",
            "message": "Bot is thinking...",
        }))
        
        # Process with LangGraph
        messages = await session.process_with_langgraph(user_input=user_input,client_id=session.client_id, image=image)
        
        # Store conversation for feedback
        bot_response = ""
        bot_intent = ""
        message_id = f"bot_{len(conversation_history[client_id])}"
        
        # Send all messages and collect bot response
        for message in messages:
            if message.get("type") == "bot_message":
                bot_response += message.get("message", "")
                message["message_id"] = message_id
                message["show_feedback"] = True
            elif message.get("type") == "intent":
                bot_intent = message.get("message", "unknown")
                # Send intent message to client for display
                await websocket.send_text(json.dumps(message))
                continue
            elif message.get("type") == "followup":
                print("followup message in frontend", message)
                pass
            await websocket.send_text(json.dumps(message))
        
        # Store in conversation history
        conversation_history[client_id].append({
            "user_input": user_input,
            "bot_response": bot_response,
            "bot_intent": bot_intent,
            "bot_message_id": message_id,
            "timestamp": datetime.now().isoformat()
        })
            
    except Exception as e:
        print(f"Error processing user input: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Sorry, I encountered an error: {str(e)}"
        }))

# Updated API endpoints
@app.get("/feedback")
async def get_feedback():
    """Get all feedback data"""
    try:
        if DATABASE_URL:
            feedback_list = await get_feedback_postgres()
            return {
                "total_feedback": len(feedback_list),
                "feedback": feedback_list,
                "source": "postgresql"
            }
        else:
            return {
                "total_feedback": len(feedback_data),
                "feedback": feedback_data,
                "source": "json"
            }
    except Exception as e:
        return {"error": str(e)}

@app.get("/feedback/stats")
async def get_feedback_stats():
    """Get feedback statistics"""
    try:
        if DATABASE_URL:
            stats = await get_feedback_stats_postgres()
            return {
                "stats": stats,
                "total": sum(stats.values()),
                "source": "postgresql"
            }
        else:
            stats = {}
            for item in feedback_data:
                feedback_type = item.get("feedback_type", "unknown")
                stats[feedback_type] = stats.get(feedback_type, 0) + 1
            
            return {
                "stats": stats,
                "total": len(feedback_data),
                "source": "json"
            }
    except Exception as e:
        return {"error": str(e)}

@app.get("/db-status")
async def db_status():
    """Check database connection status"""
    if not DATABASE_URL:
        return {
            "database": "Not configured",
            "status": "Using JSON fallback",
            "database_url_exists": False
        }
    
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.execute("SELECT 1")
        await conn.close()
        
        return {
            "database": "PostgreSQL",
            "status": "Connected",
            "database_url_exists": True
        }
    except Exception as e:
        return {
            "database": "PostgreSQL",
            "status": f"Connection failed: {str(e)}",
            "database_url_exists": True
        }

@app.get("/")
async def get_chat_interface():
    """Serve the chat interface"""
    return HTMLResponse(content="""
                        
                        
            <!DOCTYPE html>
<html>
<head>
    <title>Broadway Fashion Bot</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f5f5f5; }
        .chat-container { max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .chat-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
        .chat-messages { height: 500px; overflow-y: auto; padding: 20px; }
        .message { margin: 10px 0; padding: 10px 15px; border-radius: 18px; max-width: 70%; }
        .user-message { background: #667eea; color: white; margin-left: auto; text-align: right; }
        .bot-message { background: #f1f1f1; color: #333; white-space: pre-line; position: relative; }
        .recommendations { background: #e8f5e8; border: 1px solid #4caf50; border-radius: 10px; padding: 15px; margin: 10px 0; }
        .recommendation-item { background: white; border-radius: 8px; padding: 12px; margin: 8px 0; border-left: 4px solid #667eea; }
        .pairing-tags { font-size: 11px; color: #666; margin-top: 5px; }
        .location-header { font-weight: bold; color: #4caf50; margin-bottom: 10px; }
        .chat-input-container { display: flex; padding: 20px; }
        .chat-input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 25px; }
        .send-button { margin-left: 10px; padding: 12px 24px; background: #667eea; color: white; border: none; border-radius: 25px; cursor: pointer; }
        .typing { color: #666; font-style: italic; background: #f9f9f9; }
        .debug { background: #fff3cd; font-size: 12px; color: #856404; }
        .error { background: #f8d7da; color: #721c24; }
        .intent { background: #e3f2fd; color: #1976d2; font-size: 11px; padding: 4px 8px; border-radius: 12px; margin-bottom: 8px; border-left: 3px solid #2196f3; }
        
        .input-group {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .image-input {
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 20px;
            font-size: 12px;
            color: #666;
        }

        .image-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
        }

        .chat-input {
            margin: 0; /* Remove any existing margin */
        }

        /* Service buttons */
        .service-buttons {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin: 15px 0;
        }
        .service-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s;
            text-align: left;
        }
        .service-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        
        /* Service examples display */
        .service-examples {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
        }
        .service-examples h3 {
            color: #667eea;
            margin-top: 0;
            margin-bottom: 10px;
        }
        .service-examples p {
            color: #666;
            margin-bottom: 15px;
        }
        .example-prompts {
            display: grid;
            gap: 8px;
        }
        .example-prompt {
            background: white;
            border: 1px solid #ddd;
            border-radius: 6px;
            padding: 10px;
       
            transition: all 0.2s;
            font-size: 14px;
        }
       
        
        /* Followup questions */
        .followup-container {
            background: #fff8e1;
            border: 1px solid #ffcc02;
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
        }
        .followup-container h3 {
            color: #f57c00;
            margin-top: 0;
            margin-bottom: 15px;
        }
        .followup-form {
            display: grid;
            gap: 15px;
        }
        .followup-question {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
        }
        .followup-question label {
            display: block;
            font-weight: 500;
            margin-bottom: 8px;
            color: #333;
        }
        .followup-question select,
        .followup-question input[type="text"] {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .followup-question select:focus,
        .followup-question input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
        }
        .followup-submit {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            margin-top: 10px;
            transition: all 0.3s;
        }
        .followup-submit:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
        }
        .followup-submit:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .quick-actions {
            margin-top: 10px;
            text-align: center;
        }
        .quick-action-btn {
            background: #f0f0f0;
            border: 1px solid #ddd;
            padding: 6px 12px;
            margin: 2px;
            border-radius: 15px;
            cursor: pointer;
            font-size: 12px;
            transition: all 0.2s;
        }
        .quick-action-btn:hover {
            background: #e0e0e0;
        }
        
        /* Feedback buttons */
        .feedback-buttons { 
            display: flex; 
            gap: 8px; 
            margin-top: 10px; 
            justify-content: flex-start; 
        }
        .feedback-btn { 
            background: none; 
            border: 1px solid #ddd; 
            padding: 5px 10px; 
            border-radius: 15px; 
            cursor: pointer; 
            font-size: 12px; 
            transition: all 0.2s; 
        }
        .feedback-btn:hover { 
            background: #f0f0f0; 
        }
        .feedback-btn.selected { 
            background: #667eea; 
            color: white; 
            border-color: #667eea; 
        }
        .feedback-btn.thumbs-up.selected { 
            background: #4caf50; 
            border-color: #4caf50; 
        }
        .feedback-btn.thumbs-down.selected { 
            background: #f44336; 
            border-color: #f44336; 
        }
        .feedback-confirmation { 
            font-size: 11px; 
            color: #666; 
            margin-top: 5px; 
            font-style: italic; 
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <h1>Broadway Fashion Bot</h1>
            <p>Your Personal Style Assistant</p>
        </div>
        <div class="chat-messages" id="messages"></div>
        <div class="chat-input-container">
            <div class="input-group">
                <input type="text" id="messageInput" class="chat-input" placeholder="Describe what you're looking for..." onkeypress="handleKeyPress(event)">
                <input type="file" id="imageInput" class="image-input" accept="image/*" onchange="handleImageUpload(event)">
            </div>
            <button class="send-button" onclick="sendMessage()">Send</button>
        </div>
        <div class="quick-actions">
            <button class="quick-action-btn" onclick="sendQuickMessage('menu')">🏠 Main Menu</button>
            <button class="quick-action-btn" onclick="sendQuickMessage('1')">1️⃣ Occasions</button>
            <button class="quick-action-btn" onclick="sendQuickMessage('2')">2️⃣ Vacation</button>
            <button class="quick-action-btn" onclick="sendQuickMessage('3')">3️⃣ Pairing</button>
            <button class="quick-action-btn" onclick="sendQuickMessage('4')">4️⃣ Styling</button>
        </div>
    </div>

    <script>
        let socket;
        let clientId = Math.random().toString(36).substring(7);
        
        function initWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            socket = new WebSocket(`${protocol}//${window.location.host}/ws/${clientId}`);
            
            socket.onopen = function(event) {
                console.log('Connected to bot');
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            socket.onclose = function(event) {
                console.log('Disconnected');
            };
        }
        
        function handleMessage(data) {
            switch(data.type) {
                case 'user_message':
                    addMessage(data.message, 'user-message');
                    break;
                case 'bot_message':
                    addMessage(data.message, 'bot-message', data.message_id, data.show_feedback, data.show_service_buttons, data.services);
                    break;
                case 'service_examples':
                    displayServiceExamples(data.service_name, data.description, data.examples);
                    break;
                case 'followup':
                    displayFollowupQuestions(data.title, data.questions);
                    break;
                case 'intent':
                    // Show intent in the chat
                    addMessage(`🎯 Intent: ${data.message}`, 'intent');
                    break;
                case 'typing':
                    addMessage(data.message, 'typing');
                    setTimeout(() => {
                        document.querySelectorAll('.typing').forEach(el => el.remove());
                    }, 2000);
                    break;
                case 'recommendations':
                    displayRecommendations(data.recommendations, data.location_name);
                    break;
                case 'debug_info':
                    if (data.confidence_score !== undefined) {
                        addMessage(`Confidence: ${(data.confidence_score * 100).toFixed(1)}% | Missing: ${data.missing_parameters.join(', ') || 'None'}`, 'debug');
                    }
                    break;
                case 'error':
                    addMessage(`Error: ${data.message}`, 'error');
                    break;
                case 'feedback_confirmation':
                    showFeedbackConfirmation(data.message_id, data.message);
                    break;
            }
        }
        
        function addMessage(message, className, messageId = null, showFeedback = false, showServiceButtons = false, services = null) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${className}`;
            messageDiv.textContent = message;
            
            if (messageId) {
                messageDiv.setAttribute('data-message-id', messageId);
            }
            
            // Add service buttons if requested
            if (showServiceButtons && services) {
                const serviceButtonsDiv = document.createElement('div');
                serviceButtonsDiv.className = 'service-buttons';
                
                let buttonsHTML = '';
                Object.entries(services).forEach(([key, service]) => {
                    buttonsHTML += `
                        <button class="service-btn" onclick="selectService('${key}')">
                            ${key === '1' ? '🎭' : key === '2' ? '✈️' : key === '3' ? '👔' : '💫'} ${service.name}
                        </button>
                    `;
                });
                
                serviceButtonsDiv.innerHTML = buttonsHTML;
                messageDiv.appendChild(serviceButtonsDiv);
            }
            
            if (showFeedback && messageId) {
                const feedbackDiv = document.createElement('div');
                feedbackDiv.className = 'feedback-buttons';
                feedbackDiv.innerHTML = `
                    <button class="feedback-btn thumbs-up" onclick="sendFeedback('${messageId}', 'thumbs_up')">
                        👍 Helpful
                    </button>
                    <button class="feedback-btn thumbs-down" onclick="sendFeedback('${messageId}', 'thumbs_down')">
                        👎 Not helpful
                    </button>
                `;
                messageDiv.appendChild(feedbackDiv);
            }
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function sendFeedback(messageId, feedbackType) {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'feedback',
                    message_id: messageId,
                    feedback: feedbackType
                }));
                
                // Update UI to show selection
                const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
                if (messageDiv) {
                    const buttons = messageDiv.querySelectorAll('.feedback-btn');
                    buttons.forEach(btn => btn.classList.remove('selected'));
                    
                    const selectedBtn = messageDiv.querySelector(`.feedback-btn.${feedbackType.replace('_', '-')}`);
                    if (selectedBtn) {
                        selectedBtn.classList.add('selected');
                    }
                }
            }
        }
        
        function selectService(serviceKey) {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'service_button',
                    service: serviceKey
                }));
            }
        }
        
        function displayServiceExamples(serviceName, description, examples) {
            const messagesDiv = document.getElementById('messages');
            const examplesDiv = document.createElement('div');
            examplesDiv.className = 'service-examples';
            
            let html = `
                <h3>${serviceName}</h3>
                <p>${description}</p>
                <div class="example-prompts">
            `;
            
            examples.forEach(example => {
                html += `
                    <div class="example-prompt" >
                        ${example}
                    </div>
                `;
            });
            
            html += '</div>';
            examplesDiv.innerHTML = html;
            
            messagesDiv.appendChild(examplesDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function displayFollowupQuestions(title, questions) {
            const messagesDiv = document.getElementById('messages');
            const followupDiv = document.createElement('div');
            followupDiv.className = 'followup-container';
            
            let html = `<h3>${title}</h3><div class="followup-form">`;
            
            questions.forEach((question, index) => {
                html += `<div class="followup-question">`;
                html += `<label for="followup_${question.key}">${question.label}</label>`;
                
                if (question.type === 'select' && question.options) {
                    html += `<select id="followup_${question.key}" name="${question.key}">`;
                    html += `<option value="">Please select...</option>`;
                    question.options.forEach(option => {
                        html += `<option value="${option}">${option}</option>`;
                    });
                    html += `</select>`;
                } else if (question.type === 'text') {
                    html += `<input type="text" id="followup_${question.key}" name="${question.key}" placeholder="${question.placeholder || ''}" />`;
                }
                
                html += `</div>`;
            });
            
            html += `<button class="followup-submit" onclick="submitFollowup()">Submit Information</button>`;
            html += `</div>`;
            
            followupDiv.innerHTML = html;
            messagesDiv.appendChild(followupDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        function submitFollowup() {
            const forms = document.querySelectorAll('.followup-form');
            let form = null;
            
            // Get the most recent form or find the active one
            if (forms.length > 0) {
                form = forms[forms.length - 1]; // Get the last form
            }
            
            if (!form) {
                console.error('No followup form found');
                return;
            }
            
            // ✅ ADD THIS LINE - Get inputs from the selected form
            const inputs = form.querySelectorAll('select, input[type="text"]');
            
            const responses = {};
            
            inputs.forEach(input => {
                if (input.value.trim()) {
                    responses[input.name] = input.value.trim();
                }
            });
            
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'followup_response',
                    responses: responses
                }));
                
                // Disable the form after submission
                const submitBtn = form.querySelector('.followup-submit');
                submitBtn.disabled = true;
                submitBtn.textContent = 'Submitted ✓';
                
                inputs.forEach(input => {
                    input.disabled = true;
                });
            }
        }
        
        function showFeedbackConfirmation(messageId, confirmationMessage) {
            const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
            if (messageDiv) {
                const existingConfirmation = messageDiv.querySelector('.feedback-confirmation');
                if (existingConfirmation) {
                    existingConfirmation.remove();
                }
                
                const confirmationDiv = document.createElement('div');
                confirmationDiv.className = 'feedback-confirmation';
                confirmationDiv.textContent = confirmationMessage;
                messageDiv.appendChild(confirmationDiv);
            }
        }
        
        function displayRecommendations(recommendations, locationName) {
            const messagesDiv = document.getElementById('messages');
            const recDiv = document.createElement('div');
            recDiv.className = 'recommendations';
            
            let html = '';
            if (locationName) {
                html += `<div class="location-header">🛍️ Recommendations for ${locationName}:</div>`;
            } else {
                html += '<h4>🛍️ Recommendations:</h4>';
            }
            
            recommendations.forEach(rec => {
                html += `
                    <div class="recommendation-item">
                        <strong>${rec.title}</strong> by ${rec.brand_name}<br>
                        <small>Price: ₹${rec.price} </small>
                `;
                
                if (rec.pairing_tags && rec.pairing_tags.length > 0) {
                    html += `<div class="pairing-tags">Matching elements: ${rec.pairing_tags.slice(0, 5).join(', ')}</div>`;
                }
                
                html += `</div>`;
            });
            
            recDiv.innerHTML = html;
            messagesDiv.appendChild(recDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
        
        let selectedImageBase64 = null;

        function handleImageUpload(event) {
            const file = event.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    selectedImageBase64 = e.target.result;
                };
                reader.readAsDataURL(file);
            }
        }

        function sendMessage() {
            const messageInput = document.getElementById('messageInput');
            const message = messageInput.value.trim();
             console.log('Sending data:', message, socket.readyState);
            if (message && socket.readyState === WebSocket.OPEN) {
                const data = { message: message };
                
                // Add base64 image if uploaded
                if (selectedImageBase64) {
                    data.image = selectedImageBase64;
                }
               
                
                socket.send(JSON.stringify(data));
                messageInput.value = '';
                selectedImageBase64 = null;
                document.getElementById('imageInput').value = '';
            }
        }
        
        function sendQuickMessage(message) {
            if (socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ message: message }));
            }
        }
        
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendMessage();
            }
        }
        
        window.onload = initWebSocket;
    </script>
</body>
</html>
                        
""")
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)