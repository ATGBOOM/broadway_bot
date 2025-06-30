from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
from typing import Dict, Any
from occasionService import OccasionService
from reccomendationBot import RecommendationService
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Broadway Fashion Bot WebSocket")

# Initialize services
API_KEY = os.getenv('OPENAI_API_KEY')
occasion_service = OccasionService(API_KEY)
recommendation_service = RecommendationService()

class ChatSession:
    def __init__(self):
        self.conversation_history = ""
        self.current_parameters = None
        self.current_recommendations = None

# Store active chat sessions
chat_sessions: Dict[str, ChatSession] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    # Initialize chat session
    if client_id not in chat_sessions:
        chat_sessions[client_id] = ChatSession()
    
    session = chat_sessions[client_id]
    
    # Send welcome message
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": "👋 Welcome to Broadway Fashion! I'm here to help you find the perfect outfit. What's the occasion?",
        "timestamp": asyncio.get_event_loop().time()
    }))
    
    try:
        while True:
            # Receive message from client
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
            
            # Process the user input
            await process_user_input(websocket, session, user_input)
            
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        if client_id in chat_sessions:
            del chat_sessions[client_id]
    except Exception as e:
        print(f"WebSocket error: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Connection error: {str(e)}"
        }))

async def process_user_input(websocket: WebSocket, session: ChatSession, user_input: str):
    """Process user input and send appropriate response"""
    
    try:
        # Send typing indicator
        await websocket.send_text(json.dumps({
            "type": "typing",
            "message": "Bot is thinking...",
        }))
        
        # Extract parameters from user input
        parameters = occasion_service.extract_parameters(user_input, session.conversation_history)
        print("Extracted parameters:", parameters)
        session.current_parameters = parameters
        
        # Calculate confidence score
        confidence_score = occasion_service.get_confidence_score(parameters)
        missing_params = occasion_service.get_missing_core_parameters(parameters)
        
        print(f"Confidence: {confidence_score}, Missing: {missing_params}")
        
        # Send parameter extraction status
        await websocket.send_text(json.dumps({
            "type": "debug_info",
            "parameters": parameters,
            "confidence_score": confidence_score,
            "missing_parameters": missing_params
        }))
        
        # Check if we have enough information to recommend
        gender_available = parameters.get('core_parameters', {}).get('gender') is not None
        
        if not gender_available or confidence_score < 0.3:
            # Need more information - ask follow-up questions
            try:
                followup_message = occasion_service.generate_followup_questions(
                    missing_params, max_questions=2  # ✅ Fixed - only 2 parameters
                )
            except Exception as e:
                print(f"Error generating followup: {e}")
                followup_message = "Could you tell me more about what you're looking for? What's the occasion and are you looking for men's or women's options?"
            
            await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": followup_message,
                "message_type": "followup_question",
                "missing_parameters": missing_params,
                "confidence_score": confidence_score
            }))
            
        else:
            # We have enough info - generate recommendations
            await generate_recommendations(websocket, session, user_input, parameters, confidence_score)
        
        # Update conversation history
        session.conversation_history += f" {user_input}"
        
    except Exception as e:
        print(f"Error processing user input: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Sorry, I encountered an error: {str(e)}",
            "error_details": str(e)
        }))

async def generate_recommendations(websocket: WebSocket, session: ChatSession, user_input: str, parameters: Dict[str, Any], confidence_score: float):
    """Generate and send product recommendations"""
    
    try:
        # Get flattened tags
        try:
            parameters_flat = occasion_service.get_all_tags_flat(parameters)
            all_tags = parameters_flat["core_tags"] + parameters_flat["inferred_tags"]
        except Exception as e:
            print(f"Error getting tags: {e}")
            # Fallback: use convert_parameters_to_product_tags if get_all_tags_flat doesn't exist
            tags_result = occasion_service.convert_parameters_to_product_tags(parameters)
            all_tags = tags_result["important_tags"] + tags_result["regular_tags"]
        
        # Get gender for filtering - convert list to string
        gender = parameters.get('core_parameters', {}).get('gender')
        if isinstance(gender, list):
            gender = gender[0] if gender else None
        
        print(f"All tags for recommendation: {all_tags}")
        print(f"Gender filter: {gender}")
        
        # Generate recommendations
        recommendations = recommendation_service.get_recommendations(
            user_input, 
            all_tags, 
            gender=[gender] if gender else None,  # ✅ Pass as list like your method expects
            category_name=None,
            conversation_history=session.conversation_history
        )
        
        session.current_recommendations = recommendations
        print(f"Generated {len(recommendations)} recommendations")
        
        # Generate insightful message
        try:
            insightful_message = occasion_service.generate_insightful_statement(
                user_input, 
                session.conversation_history, 
                recommendations, 
                parameters
            )
        except Exception as e:
            print(f"Error generating insightful statement: {e}")
            if recommendations:
                insightful_message = f"Great! I found {len(recommendations)} perfect options for you!"
            else:
                insightful_message = "I couldn't find any products matching your requirements. Let me ask a few more questions."
            
        await websocket.send_text(json.dumps({
            "type": "bot_message",
            "message": insightful_message,
            "message_type": "recommendation_intro"
        }))
        
        if recommendations:
            # Send recommendations
            await websocket.send_text(json.dumps({
                "type": "recommendations",
                "recommendations": [
                    {
                        "id": i + 1,
                        "product_id": rec['product_id'],
                        "title": rec['title'],
                        "brand_name": rec['brand_name'],
                        "price": rec.get('price', 'N/A'),
                        "matched_important_tags": rec['matched_important_tags'],
                        "matched_regular_tags": rec['matched_regular_tags'],
                        "total_score": rec['total_score']
                    }
                    for i, rec in enumerate(recommendations)
                ]
            }))
            
            # If confidence is still low, ask follow-up questions
            if confidence_score < 0.5:
                missing_params = occasion_service.get_missing_core_parameters(parameters)
                if missing_params:
                    try:
                        followup_message = occasion_service.generate_followup_questions(
                            missing_params, max_questions=1  # ✅ Fixed - only 2 parameters
                        )
                        
                        await websocket.send_text(json.dumps({
                            "type": "bot_message", 
                            "message": f"I'd love to refine these recommendations! {followup_message}",
                            "message_type": "followup_after_recommendations"
                        }))
                    except Exception as e:
                        print(f"Error generating followup after recommendations: {e}")
        else:
            await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": "I couldn't find any products matching your requirements. Could you try describing what you're looking for differently?",
                "message_type": "no_recommendations"
            }))
            
    except Exception as e:
        print(f"Error generating recommendations: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Error generating recommendations: {str(e)}"
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
        .bot-message { background: #f1f1f1; color: #333; }
        .recommendations { background: #e8f5e8; border: 1px solid #4caf50; border-radius: 10px; padding: 15px; margin: 10px 0; }
        .recommendation-item { background: white; border-radius: 8px; padding: 12px; margin: 8px 0; border-left: 4px solid #667eea; }
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
            <input type="text" id="messageInput" class="chat-input" placeholder="Tell me about the occasion..." onkeypress="handleKeyPress(event)">
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
                addMessage('Connected to Broadway Fashion Bot!', 'debug');
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            socket.onclose = function(event) {
                console.log('Disconnected');
                addMessage('Connection lost. Refresh to reconnect.', 'error');
            };
            
            socket.onerror = function(error) {
                console.error('WebSocket error:', error);
                addMessage('Connection error occurred.', 'error');
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
                    displayRecommendations(data.recommendations);
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
        
        function displayRecommendations(recommendations) {
            const messagesDiv = document.getElementById('messages');
            const recDiv = document.createElement('div');
            recDiv.className = 'recommendations';
            
            let html = '<h4>🛍️ Recommendations:</h4>';
            recommendations.forEach(rec => {
                html += `
                    <div class="recommendation-item">
                        <strong>${rec.title}</strong> by ${rec.brand_name}<br>
                        <small>Price: ₹${rec.price} | Score: ${rec.total_score}</small><br>
                        <small>Tags: ${rec.matched_important_tags.join(', ')}</small>
                    </div>
                `;
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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Broadway Fashion Bot WebSocket"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)