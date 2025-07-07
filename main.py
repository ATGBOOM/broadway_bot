from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
import os
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

# Your existing imports
from occasionService import OccasionService
from reccomendationBot import RecommendationService
from pairingService import PairingService
from vacationService import VacationService  
from conversationService import ConversationService
from generalService import GeneralService
from genderService import GenderService

# NEW: Import LangGraph integration
from fashion_graph import ChatSession

app = FastAPI(title="Broadway Fashion Bot WebSocket")

# Initialize JSON file for feedback
FEEDBACK_FILE = "feedback.json"

def load_feedback():
    """Load existing feedback from JSON file"""
    if Path(FEEDBACK_FILE).exists():
        try:
            with open(FEEDBACK_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading feedback file: {e}")
            return []
    return []

def save_feedback_to_file(feedback_list):
    """Save feedback list to JSON file"""
    try:
        with open(FEEDBACK_FILE, 'w', encoding='utf-8') as f:
            json.dump(feedback_list, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving feedback file: {e}")

# Load existing feedback on startup
feedback_data = load_feedback()

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
    print("✅ Services initialized successfully")
except Exception as e:
    print(f"❌ Error initializing services: {e}")
    raise

# Store active chat sessions and conversation history
chat_sessions: Dict[str, ChatSession] = {}
conversation_history: Dict[str, list] = {}

def save_feedback(client_id: str, user_input: str, bot_response: str, bot_intent: str, feedback_type: str):
    """Save feedback to JSON file"""
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
        
        print(f"✅ Feedback saved: {feedback_type} for client {client_id}, intent: {bot_intent}")
    except Exception as e:
        print(f"❌ Error saving feedback: {e}")

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
        'gender' : GenderService()
    }
    
    if client_id not in chat_sessions:
        chat_sessions[client_id] = ChatSession(services_dict)
        chat_sessions[client_id].client_id = client_id
        conversation_history[client_id] = []
    
    session = chat_sessions[client_id]
    
    # Send initial message
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": "👋 Welcome to Broadway Fashion! I'm here to help you find the perfect outfit. What would you like help with today?",
        "timestamp": asyncio.get_event_loop().time(),
        "message_id": f"bot_{len(conversation_history[client_id])}"
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Handle feedback
            if message_data.get("type") == "feedback":
                message_id = message_data.get("message_id")
                feedback_type = message_data.get("feedback")  # "thumbs_up" or "thumbs_down"
                
                # Find the conversation pair
                history = conversation_history[client_id]
                for i, entry in enumerate(history):
                    if entry.get("bot_message_id") == message_id:
                        save_feedback(
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
            
            user_input = message_data.get("message", "").strip()
            
            if not user_input:
                continue
            
            # Echo user message
            await websocket.send_text(json.dumps({
                "type": "user_message", 
                "message": user_input,
                "timestamp": asyncio.get_event_loop().time()
            }))
            
            # Process with new LangGraph function
            await process_user_input_new(websocket, session, user_input, client_id)
            
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        if client_id in chat_sessions:
            del chat_sessions[client_id]
        if client_id in conversation_history:
            del conversation_history[client_id]
    except Exception as e:
        print(f"WebSocket error: {e}")

async def process_user_input_new(websocket: WebSocket, session: ChatSession, user_input: str, client_id: str):
    """New process function using LangGraph"""
    
    try:
        # Show typing indicator
        await websocket.send_text(json.dumps({
            "type": "typing",
            "message": "Bot is thinking...",
        }))
        
        # Process with LangGraph
        messages = await session.process_with_langgraph(user_input, session.client_id)
        
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
                print(message, bot_intent)
                # Send intent message to client for display
                await websocket.send_text(json.dumps(message))
                continue
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
            <input type="text" id="messageInput" class="chat-input" placeholder="Choose 1, 2, or 3, or describe what you're looking for..." onkeypress="handleKeyPress(event)">
            <button class="send-button" onclick="sendMessage()">Send</button>
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
                    addMessage(data.message, 'bot-message', data.message_id, data.show_feedback);
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
        
        function addMessage(message, className, messageId = null, showFeedback = false) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${className}`;
            messageDiv.textContent = message;
            
            if (messageId) {
                messageDiv.setAttribute('data-message-id', messageId);
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
        
        function sendMessage() {
            const input = document.getElementById('messageInput');
            const message = input.value.trim();
            
            if (message && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({ message: message }));
                input.value = '';
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

@app.get("/feedback")
async def get_feedback():
    """Get all feedback data"""
    try:
        return {
            "total_feedback": len(feedback_data),
            "feedback": feedback_data
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/feedback/stats")
async def get_feedback_stats():
    """Get feedback statistics"""
    try:
        stats = {}
        for item in feedback_data:
            feedback_type = item.get("feedback_type", "unknown")
            stats[feedback_type] = stats.get(feedback_type, 0) + 1
        
        return {
            "stats": stats,
            "total": len(feedback_data)
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug")
async def debug_environment():
    """Debug endpoint"""
    api_key = os.getenv('OPENAI_API_KEY')
    return {
        "api_key_exists": bool(api_key),
        "api_key_length": len(api_key) if api_key else 0,
        "environment_vars": list(os.environ.keys())
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Broadway Fashion Bot WebSocket"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)