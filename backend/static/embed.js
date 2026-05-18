// AI Chatbot Widget Embed Script
(function() {
    // Configuration from window.chatbotConfig
    const config = window.chatbotConfig || {};
    const botId = config.botId || 1;
    const apiUrl = config.apiUrl || "http://localhost:8000";
    const primaryColor = config.primaryColor || "#007bff";
    const welcomeMessage = config.welcomeMessage || "Hello! How can I help you today?";
    
    // Don't initialize twice
    if (window.chatbotInitialized) return;
    window.chatbotInitialized = true;
    
    // Create chat widget container
    const widgetContainer = document.createElement('div');
    widgetContainer.id = 'ai-chatbot-widget';
    document.body.appendChild(widgetContainer);
    
    // Add styles
    const styles = document.createElement('style');
    styles.textContent = `
        .chat-bubble {
            position: fixed;
            bottom: 20px;
            right: 20px;
            width: 60px;
            height: 60px;
            border-radius: 30px;
            background: ${primaryColor};
            color: white;
            border: none;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s;
        }
        .chat-bubble:hover {
            transform: scale(1.05);
        }
        .chat-window {
            position: fixed;
            bottom: 90px;
            right: 20px;
            width: 380px;
            height: 500px;
            background: white;
            border-radius: 12px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 9999;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        .chat-header {
            background: ${primaryColor};
            color: white;
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 15px;
            background: #f8f9fa;
        }
        .message-user {
            text-align: right;
            margin-bottom: 10px;
        }
        .message-user span {
            background: ${primaryColor};
            color: white;
            padding: 8px 12px;
            border-radius: 18px;
            display: inline-block;
            max-width: 70%;
            word-wrap: break-word;
        }
        .message-bot {
            text-align: left;
            margin-bottom: 10px;
        }
        .message-bot span {
            background: white;
            color: #333;
            padding: 8px 12px;
            border-radius: 18px;
            display: inline-block;
            max-width: 70%;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
            word-wrap: break-word;
        }
        .chat-input-area {
            padding: 15px;
            background: white;
            border-top: 1px solid #ddd;
            display: flex;
            gap: 10px;
        }
        .chat-input {
            flex: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
        }
        .chat-send {
            padding: 10px 20px;
            background: ${primaryColor};
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
        }
        .chat-send:hover {
            opacity: 0.9;
        }
        .typing-indicator {
            text-align: left;
            margin-bottom: 10px;
        }
        .typing-indicator span {
            background: white;
            color: #666;
            padding: 8px 12px;
            border-radius: 18px;
            display: inline-block;
        }
        @media (max-width: 480px) {
            .chat-window {
                width: 100vw;
                height: 100vh;
                bottom: 0;
                right: 0;
                border-radius: 0;
            }
        }
    `;
    document.head.appendChild(styles);
    
    // Create widget HTML
    widgetContainer.innerHTML = `
        <button class="chat-bubble" id="chat-toggle-btn">💬</button>
        <div class="chat-window" id="chat-window">
            <div class="chat-header">
                <span>💬 Customer Support</span>
                <button id="chat-close-btn" style="background:none;border:none;color:white;font-size:20px;cursor:pointer;">✕</button>
            </div>
            <div class="chat-messages" id="chat-messages">
                <div class="message-bot">
                    <span>${welcomeMessage}</span>
                </div>
            </div>
            <div class="chat-input-area">
                <input type="text" class="chat-input" id="chat-input" placeholder="Type your question...">
                <button class="chat-send" id="chat-send-btn">Send</button>
            </div>
        </div>
    `;
    
    // Get elements
    const toggleBtn = document.getElementById('chat-toggle-btn');
    const closeBtn = document.getElementById('chat-close-btn');
    const chatWindow = document.getElementById('chat-window');
    const sendBtn = document.getElementById('chat-send-btn');
    const chatInput = document.getElementById('chat-input');
    const messagesDiv = document.getElementById('chat-messages');
    
    // Open chat
    toggleBtn.onclick = () => {
        chatWindow.style.display = 'flex';
    };
    
    // Close chat
    closeBtn.onclick = () => {
        chatWindow.style.display = 'none';
    };
    
    // Send message function
    async function sendMessage() {
        const message = chatInput.value.trim();
        if (!message) return;
        
        // Add user message
        const userMsgDiv = document.createElement('div');
        userMsgDiv.className = 'message-user';
        userMsgDiv.innerHTML = `<span>${escapeHtml(message)}</span>`;
        messagesDiv.appendChild(userMsgDiv);
        
        chatInput.value = '';
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Show typing indicator
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = '<span>Typing...</span>';
        messagesDiv.appendChild(typingDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        try {
            const response = await fetch(`${apiUrl}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    bot_id: botId,
                    message: message
                })
            });
            
            if (!response.ok) throw new Error('Network response was not ok');
            
            const data = await response.json();
            
            // Remove typing indicator
            const typingEl = document.getElementById('typing-indicator');
            if (typingEl) typingEl.remove();
            
            // Add bot response
            const botMsgDiv = document.createElement('div');
            botMsgDiv.className = 'message-bot';
            botMsgDiv.innerHTML = `<span>${escapeHtml(data.answer)}</span>`;
            messagesDiv.appendChild(botMsgDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
            
        } catch (error) {
            // Remove typing indicator
            const typingEl = document.getElementById('typing-indicator');
            if (typingEl) typingEl.remove();
            
            // Show error
            const errorDiv = document.createElement('div');
            errorDiv.className = 'message-bot';
            errorDiv.innerHTML = `<span style="background:#f8d7da;color:#721c24;">Error: ${escapeHtml(error.message)}</span>`;
            messagesDiv.appendChild(errorDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    }
    
    sendBtn.onclick = sendMessage;
    chatInput.onkeypress = (e) => {
        if (e.key === 'Enter') sendMessage();
    };
    
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
})();
