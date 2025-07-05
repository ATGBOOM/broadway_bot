from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
import os
from typing import Dict, Any

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

# Store active chat sessions
chat_sessions: Dict[str, ChatSession] = {}

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
        chat_sessions[client_id].client_id = client_id  # Add client_id to session
    
    session = chat_sessions[client_id]
    
    # Send initial message
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": "👋 Welcome to Broadway Fashion! I'm here to help you find the perfect outfit. What would you like help with today?",
        "timestamp": asyncio.get_event_loop().time()
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
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
            await process_user_input_new(websocket, session, user_input)
            
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        if client_id in chat_sessions:
            del chat_sessions[client_id]
    except Exception as e:
        print(f"WebSocket error: {e}")

async def process_user_input_new(websocket: WebSocket, session: ChatSession, user_input: str):
    """New process function using LangGraph"""
    
    try:
        # Show typing indicator
        await websocket.send_text(json.dumps({
            "type": "typing",
            "message": "Bot is thinking...",
        }))
        
        # Process with LangGraph
        messages = await session.process_with_langgraph(user_input, session.client_id)
        
        # Send all messages
        for message in messages:
            await websocket.send_text(json.dumps(message))
            
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
        .bot-message { background: #f1f1f1; color: #333; white-space: pre-line; }
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
                    addMessage(data.message, 'bot-message');
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
            }
        }
        
        function addMessage(message, className) {
            const messagesDiv = document.getElementById('messages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${className}`;
            messageDiv.textContent = message;
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
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
                
                // Add pairing tags if available
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