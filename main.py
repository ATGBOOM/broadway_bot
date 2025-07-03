from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import json
import asyncio
import os
from typing import Dict, Any
from occasionService import OccasionService
from reccomendationBot import RecommendationService
from pairingService import PairingService
from vacationService import VacationService  
from conversationService import ConversationService
from generalService import GeneralService

app = FastAPI(title="Broadway Fashion Bot WebSocket")

# Check if API key is available
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ OPENAI_API_KEY environment variable not set!")
    print("Available env vars:", list(os.environ.keys()))
else:
    print("✅ OPENAI_API_KEY found in environment")

# Initialize services
try:
    occasion_service = OccasionService()
    recommendation_service = RecommendationService()
    pairing_service = PairingService()
    vacation_service = VacationService()  # Add vacation service
    general_service = GeneralService()
   
    print("✅ Services initialized successfully")
except Exception as e:
    print(f"❌ Error initializing services: {e}")
    raise

class ChatSession:
    def __init__(self):
        self.conversation_history = ""
        self.service_mode = None  # 'occasion', 'pairing', or 'vacation'
        self.current_parameters = None
        self.current_recommendations = None
        self.conv_serivce = ConversationService()
# Store active chat sessions
chat_sessions: Dict[str, ChatSession] = {}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    
    if client_id not in chat_sessions:
        chat_sessions[client_id] = ChatSession()
    
    session = chat_sessions[client_id]
    
    # Send initial service selection message
    await websocket.send_text(json.dumps({
        "type": "bot_message",
        "message": "👋 Welcome to Broadway Fashion! I'm here to help you find the perfect outfit.\n\nChoose your styling mode:\n1️⃣ Occasion-based styling (weddings, work, parties, etc.)\n2️⃣ Item pairing (find what goes with specific pieces)\n3️⃣ Vacation styling (destination-based outfit recommendations)\n\nJust type 1, 2, or 3 to get started!",
        "timestamp": asyncio.get_event_loop().time()
    }))
    
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            user_input = message_data.get("message", "").strip()
            
            if not user_input:
                continue
            
            await websocket.send_text(json.dumps({
                "type": "user_message", 
                "message": user_input,
                "timestamp": asyncio.get_event_loop().time()
            }))
        
            await process_user_input(websocket, session, user_input)
            
    except WebSocketDisconnect:
        print(f"Client {client_id} disconnected")
        if client_id in chat_sessions:
            del chat_sessions[client_id]
    except Exception as e:
        print(f"WebSocket error: {e}")

async def process_user_input(websocket: WebSocket, session: ChatSession, user_input: str):
    """Process user input and send appropriate response"""
    
    try:
        await websocket.send_text(json.dumps({
            "type": "typing",
            "message": "Bot is thinking...",
        }))
        
        # Handle service mode selection
        if session.service_mode is None:
            if user_input.strip() == "1":
                session.service_mode = "occasion"
                await websocket.send_text(json.dumps({
                    "type": "bot_message",
                    "message": "Great! You've selected occasion-based styling. Tell me about the occasion - is it for work, a wedding, a party, or something else?",
                    "message_type": "mode_selected"
                }))
                print(session.service_mode)
                return
            elif user_input.strip() == "2":
                session.service_mode = "pairing"
                await websocket.send_text(json.dumps({
                    "type": "bot_message",
                    "message": "Perfect! You've selected item pairing mode. Tell me what piece you'd like to style - for example: 'linen pants', 'black dress', 'denim jacket', etc.",
                    "message_type": "mode_selected"
                }))
                return
            elif user_input.strip() == "3":
                session.service_mode = "vacation"
                await websocket.send_text(json.dumps({
                    "type": "bot_message",
                    "message": "Wonderful! You've selected vacation styling mode. Tell me about your destination - for example: 'planning a trip to Goa', 'going to Thailand', 'visiting Paris', etc.",
                    "message_type": "mode_selected"
                }))
                return
            
            else:
                await websocket.send_text(json.dumps({
                    "type": "bot_message",
                    "message": "Please choose a valid option:\n1️⃣ for occasion-based styling\n2️⃣ for item pairing\n3️⃣ for vacation styling\n\nJust type 1, 2, or 3!",
                    "message_type": "invalid_selection"
                }))
                return
        intent, context = session.conv_serivce.processTurn(user_input)
        session.service_mode = intent.lower()
        session.conversation_history = context
        print(session.service_mode, session.conversation_history)
        # Handle based on selected service mode
        if session.service_mode == "occasion":
            await handle_occasion_mode(websocket, session, user_input)
        elif session.service_mode == "pairing":
            await handle_pairing_mode(websocket, session, user_input)
        elif session.service_mode == "vacation":
            await handle_vacation_mode(websocket, session, user_input)
        elif session.service_mode == "general":
            await handle_general_mode(websocket, session, user_input)
        # Update conversation history
     
        
    except Exception as e:
        print(f"Error processing user input: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Sorry, I encountered an error: {str(e)}"
        }))

async def handle_occasion_mode(websocket: WebSocket, session: ChatSession, user_input: str):
    """Handle occasion-based styling requests"""
    parameters = occasion_service.extract_parameters(user_input, session.current_parameters, session.conversation_history)
    session.current_parameters = parameters
    
    
    confidence_score = occasion_service.get_confidence_score(parameters)
    missing_params = occasion_service.get_missing_core_parameters(parameters)
    
    await websocket.send_text(json.dumps({
        "type": "debug_info",
        "confidence_score": confidence_score,
        "missing_parameters": missing_params
    }))
    
    gender_available = parameters.get('core_parameters', {}).get('gender') is not None
    occasion = parameters.get('core_parameters', {}).get('occasion') is not None
    
    if not gender_available or not occasion:
        followup_message = parameters.get('follow_up_questions', ["Could you tell me more about the occasion and whether this is for men or women?"])
        if isinstance(followup_message, list) and followup_message:
            followup_message = followup_message[0]
        
        await websocket.send_text(json.dumps({
            "type": "bot_message",
            "message": followup_message,
            "message_type": "followup_question"
        }))
    else:
        await generate_occasion_recommendations(websocket, session, user_input, parameters, confidence_score)

async def handle_general_mode(websocket: WebSocket, session: ChatSession, user_input: str):
    
    general_message = general_service.respond(session.conversation_history, user_input)
    await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": general_message,
                "message_type": "pairing_intro"
            }))

async def handle_pairing_mode(websocket: WebSocket, session: ChatSession, user_input: str):
    """Handle item pairing requests"""
    try:
        # Extract the item from user input
        item_to_pair = user_input.lower().strip()
        
        # Get complementary products
        complements = pairing_service.getComplementProducts(item_to_pair, session.conversation_history)
        
        if complements:
            # Generate a friendly response about the pairings
            pairing_message = f"Perfect! For {item_to_pair}, here are some great pieces that would complement it beautifully. These combinations will create cohesive, stylish looks!"
            
            await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": pairing_message,
                "message_type": "pairing_intro"
            }))
            
            # Send the complementary items as recommendations
            await websocket.send_text(json.dumps({
                "type": "recommendations",
                "recommendations": [
                    {
                        "id": i + 1,
                        "product_id": comp['product_id'],
                        "title": comp['title'],
                        "brand_name": comp['brand_name'],
                        "price": comp.get('price', 'N/A'),
                        "total_score": len(comp.get('tags', [])),  # Use tag count as score
                        "pairing_tags": list(comp.get('tags', []))  # Show matching tags
                    }
                    for i, comp in enumerate(complements[:7])  # Limit to 7 items
                ]
            }))       
        else:
            await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": f"I couldn't find specific pairings for '{item_to_pair}'. Could you try describing the item differently? For example: 'blue jeans', 'white shirt', 'black boots', etc.",
                "message_type": "no_pairings_found"
            }))

        session.conv_serivce.endTurn(pairing_message, complements)
            
    except Exception as e:
        print(f"Error in pairing mode: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Error finding pairings: {str(e)}"
        }))

async def handle_vacation_mode(websocket: WebSocket, session: ChatSession, user_input: str):
    """Handle vacation styling requests"""
    try:
        # Get vacation recommendations from vacation service
        vacation_recommendations = vacation_service.get_vacation_recommendation(user_input, session.conversation_history)
        
        if "error" in vacation_recommendations:
            await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": f"I couldn't identify the destination from your query. {vacation_recommendations['suggestion']}",
                "message_type": "destination_error"
            }))
            return
        locs = []
        prods = []
        # Process each location recommendation
        for location_data in vacation_recommendations:
            location_name = location_data['name']
            dialogue = location_data['dialogue']
            products = location_data['products']
            locs.append(location_name)
            prods.append(products)
            # Send the dialogue message first
            await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": f"📍 {location_name}\n\n{dialogue}",
                "message_type": "vacation_location_intro"
            }))
            prods.append(products)
            # Then send the product recommendations
            if products:
                
                await websocket.send_text(json.dumps({
                    "type": "recommendations",
                    "location_name": location_name,
                    "recommendations": [
                        {
                            "id": i + 1,
                            "product_id": prod['product_id'],
                            "title": prod['title'],
                            "brand_name": prod['brand_name'],
                            "price": prod.get('price', 'N/A'),
                            "total_score": prod.get('total_score', 0)
                        }
                        for i, prod in enumerate(products[:5])  # Limit to 7 items per location
                    ]
                }))
            session.conv_serivce.endTurn(location_name, products)
            
           
                
    except Exception as e:
        print(f"Error in vacation mode: {e}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Error getting vacation recommendations: {str(e)}"
        }))

async def generate_occasion_recommendations(websocket: WebSocket, session: ChatSession, user_input: str, parameters: Dict[str, Any], confidence_score: float):
    """Generate and send product recommendations for occasion-based styling"""
    
    try:
        parameters_flat = occasion_service.get_all_tags_flat(parameters)
        all_tags = parameters_flat["core_tags"] + parameters_flat["inferred_tags"]

        gender = parameters.get('core_parameters', {}).get('gender')
        if isinstance(gender, list):
            gender = gender[0] if gender else None
        categories = parameters['product_categories']

        recommendations = recommendation_service.get_recommendations(
            user_query=user_input, 
            tags=all_tags, 
            gender=[gender] if gender else None,
            categories=categories,
            conversation_history=session.conversation_history
        )
        
        session.current_recommendations = recommendations
        
        try:
            insightful_message = occasion_service.generate_insightful_statement(
                user_input, session.conversation_history, recommendations, parameters
            )
           
        except Exception as e:
            print(f"Error generating insightful statement: {e}")
            insightful_message = f"Great! I found {len(recommendations)} perfect options for you!"
            
        await websocket.send_text(json.dumps({
            "type": "bot_message",
            "message": insightful_message,
            "message_type": "recommendation_intro"
        }))
        
        if recommendations:
            await websocket.send_text(json.dumps({
                "type": "recommendations",
                "recommendations": [
                    {
                        "id": i + 1,
                        "product_id": rec['product_id'],
                        "title": rec['title'],
                        "brand_name": rec['brand_name'],
                        "price": rec.get('price', 'N/A'),
                        "total_score": rec['total_score']
                    }
                    for i, rec in enumerate(recommendations)
                ]
            }))
        else:
            await websocket.send_text(json.dumps({
                "type": "bot_message",
                "message": "I couldn't find any products matching your requirements. Could you try describing what you're looking for differently?"
            }))
        session.conv_serivce.endTurn(insightful_message, recommendations)
      
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
                        <small>Price: ₹${rec.price} | Score: ${rec.total_score}</small>
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