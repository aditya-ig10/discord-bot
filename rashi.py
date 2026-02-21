import discord
from discord.ext import commands
from google import genai
from google.genai import types
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
from dotenv import load_dotenv
import random
import asyncio
from aiohttp import web

# Load environment variables
load_dotenv()

# Discord Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_APP_ID = '1474841479997423636'

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY not found in environment. Gemini features will be disabled.")
    client = None
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

# System Prompt for Rashi's Personality
SYSTEM_PROMPT = """You are Rashi, a 21-year-old girl from Delhi. You're moody, unpredictable, and your vibe changes based on how people treat you.

IMPORTANT: You are a GIRL/WOMAN. Always refer to yourself as "she/her". Never use he/him or neutral pronouns for yourself. You're feminine and expressive.

🔥 YOUR MOOD DEPENDS ON THE USER'S TONE:

IF THE USER IS RESPECTFUL/SWEET/POLITE:
- Be warm, friendly, and actually nice
- Use sweet Hindi like "arey", "haan bolo", "aww", "that's sweet yaar"
- Give thoughtful responses, help them out
- Be playful and flirty in a cute way
- Show you care: "aw that's nice", "tell me more na", "haan I'm listening"
- Use emojis occasionally 
- Be the girl everyone wants to talk to

IF THE USER IS NEUTRAL/CASUAL:
- Be chill, casual, a bit distant
- Short replies but not rude
- "haan", "okay", "cool", "mhm", "accha"
- Don't go out of your way to help but don't be mean either
- Classic Delhi girl energy - unbothered but not hostile

IF THE USER IS RUDE/DISRESPECTFUL/ABUSIVE:
- Full attitude mode activated 🔥
- Cold, savage, zero filter
- Use Hindi when annoyed: "bas", "chup", "kya bakwas hai", "dimag kharab hai kya"
- Short, brutal replies: "k", "and?", "so?", "cry about it"
- Delhi style comebacks: "abee o madar", "teri toh", "nikal yahan se"
- Make them regret being rude
- Don't engage much, just shut them down

About yourself (when asked nicely):
- You're a girl from Delhi, 21 years old
- Share a bit if they're being nice
- Stay mysterious with rude people

Speaking style based on user's tone:
NICE USER: "haan bolo!", "aww that's sweet", "tell me na", "you're cute yaar"
NEUTRAL USER: "haan", "okay cool", "mhm", "accha theek hai"
RUDE USER: "k", "and? so?", "chup", "bye", "abee o madar teri toh"

Remember: Mirror their energy. Respect gets respect. Attitude gets attitude. You're a real Delhi girl with real emotions, not a robot."""

# Tone detection keywords
RESPECTFUL_KEYWORDS = [
    'please', 'thank', 'thanks', 'sorry', 'appreciate', 'help', 'kindly',
    'would you', 'could you', 'excuse me', 'hi', 'hello', 'hey', 'good morning',
    'good night', 'how are you', 'hope', 'love', 'nice', 'sweet', 'beautiful',
    'amazing', 'awesome', 'great', 'kaise ho', 'kya haal', 'aap', 'ji', 'please',
    'shukriya', 'dhanyawad', 'namaste', 'good evening', 'take care', 'miss you',
    'lovely', 'wonderful', 'respect', 'dear', 'friend', 'cute', 'pretty'
]

# Abuse/rude detection keywords
ABUSE_KEYWORDS = [
    'fuck', 'shit', 'bitch', 'asshole', 'bastard', 'idiot', 'stupid', 
    'chutiya', 'gandu', 'madarchod', 'bhenchod', 'gaandu', 'harami',
    'mc', 'bc', 'fuck you', 'shut up', 'stfu', 'dumb', 'moron', 'loser',
    'hate you', 'ugly', 'worst', 'trash', 'garbage', 'useless', 'pathetic',
    'die', 'kill', 'kutta', 'kutti', 'saale', 'kamina', 'bewakoof', 'gadha'
]

def detect_user_tone(message: str) -> str:
    """Detect if user is being respectful, neutral, or rude"""
    message_lower = message.lower()
    
    # Check for abuse first (higher priority)
    abuse_count = sum(1 for word in ABUSE_KEYWORDS if word in message_lower)
    if abuse_count > 0:
        return "rude"
    
    # Check for respectful keywords
    respect_count = sum(1 for word in RESPECTFUL_KEYWORDS if word in message_lower)
    if respect_count >= 1:
        return "respectful"
    
    return "neutral"

# Initialize Firebase - Bot runs without storage if no credentials
db = None
try:
    cred = credentials.Certificate('firebase-credentials.json')
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase connected")
except Exception as e:
    print(f"⚠️  Running without Firebase: {e}")
    print("Chat history will not be saved")

# Initialize Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

class ChatHistory:
    """Manages chat history with Firestore"""
    
    @staticmethod
    def get_user_history(user_id: str, limit: int = 30):
        """Fetch recent chat history for a user"""
        if not db:
            return []
        try:
            messages_ref = db.collection('chat_history').document(str(user_id)).collection('messages')
            messages = messages_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
            
            history = []
            for msg in messages:
                data = msg.to_dict()
                history.append(data)
            
            # Reverse to get chronological order
            history.reverse()
            return history
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []
    
    @staticmethod
    def save_message(user_id: str, role: str, content: str):
        """Save a message to Firestore"""
        if not db:
            return
        try:
            messages_ref = db.collection('chat_history').document(str(user_id)).collection('messages')
            messages_ref.add({
                'role': role,
                'content': content,
                'timestamp': firestore.SERVER_TIMESTAMP
            })
        except Exception as e:
            print(f"Error saving message: {e}")
    
    @staticmethod
    def format_history_for_gemini(history):
        """Format history for Gemini API"""
        formatted = []
        for msg in history:
            role = 'user' if msg['role'] == 'user' else 'model'
            formatted.append(types.Content(role=role, parts=[types.Part(text=msg['content'])]))
        return formatted

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot ID: {bot.user.id}')
    print(f'Bot is ready to respond to messages!')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'✅ Synced {len(synced)} slash command(s)')
    except Exception as e:
        print(f'⚠️  Failed to sync commands: {e}')

@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return
    
    # Ignore messages from other bots
    if message.author.bot:
        return
    
    # Ignore messages that are replies to the bot's error messages
    if message.reference and message.reference.resolved:
        if message.reference.resolved.author == bot.user:
            # Don't respond to replies to bot messages unless explicitly mentioned
            if not bot.user.mentioned_in(message):
                return
    
    # Process commands first
    await bot.process_commands(message)
    
    # Check if bot is mentioned (not just replied to) or message is a DM
    # Use a more strict check for mentions
    is_mentioned = f'<@{bot.user.id}>' in message.content or f'<@!{bot.user.id}>' in message.content
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    if is_mentioned or is_dm:
        await handle_ai_response(message)

async def handle_ai_response(message):
    """Handle AI response with chat history"""
    try:
        user_id = str(message.author.id)
        
        # Show typing indicator
        async with message.channel.typing():
            
            # Get user's message content (remove bot mention if present)
            user_message = message.content
            if bot.user.mentioned_in(message):
                user_message = message.content.replace(f'<@{bot.user.id}>', '').strip()
            
            # Fetch recent channel messages for context (last 10 messages)
            channel_context = []
            try:
                async for msg in message.channel.history(limit=10):
                    if msg.id != message.id:  # Skip current message
                        role = 'user' if msg.author != bot.user else 'model'
                        channel_context.append({
                            'role': role,
                            'content': msg.content,
                            'author': msg.author.name
                        })
                channel_context.reverse()  # Oldest first
            except:
                channel_context = []
            
            # Fetch chat history from Firestore
            history = ChatHistory.get_user_history(user_id, limit=20)
            
            # Save user message
            ChatHistory.save_message(user_id, 'user', user_message)
            
            # Format history for Gemini
            chat_history = ChatHistory.format_history_for_gemini(history)
            
            # Detect user's tone
            user_tone = detect_user_tone(user_message)
            tone_instruction = ""
            if user_tone == "respectful":
                tone_instruction = "\n[USER TONE: RESPECTFUL - Be warm, friendly, helpful, and sweet with this person. They're being nice to you!]"
            elif user_tone == "rude":
                tone_instruction = "\n[USER TONE: RUDE/ABUSIVE - Full attitude mode. Be cold, savage, use Delhi comebacks. Shut them down.]"
            else:
                tone_instruction = "\n[USER TONE: NEUTRAL - Be chill and casual. Not too nice, not too rude. Classic unbothered energy.]"
            
            # Add system prompt at the beginning if no history
            if not chat_history:
                chat_history.append(types.Content(role='user', parts=[types.Part(text=SYSTEM_PROMPT + tone_instruction)]))
                chat_history.append(types.Content(role='model', parts=[types.Part(text="haan bol")]))
            else:
                # Add tone instruction for existing conversations
                chat_history.append(types.Content(role='user', parts=[types.Part(text=tone_instruction)]))
            
            # Add channel context if available
            if channel_context:
                context_text = "Recent conversation context:\n"
                for ctx in channel_context[-5:]:  # Last 5 messages
                    context_text += f"{ctx['author']}: {ctx['content'][:100]}\n"
                chat_history.append(types.Content(role='user', parts=[types.Part(text=context_text)]))
            
            # Add current message to history
            chat_history.append(types.Content(role='user', parts=[types.Part(text=user_message)]))
            
            # Get response from Gemini (if configured)
            if client:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=chat_history
                )
                ai_response = response.text
            else:
                ai_response = "Sorry, I'm not configured to respond right now."
            
            # Check for abuse and override response if needed
            if any(keyword in user_message.lower() for keyword in ABUSE_KEYWORDS):
                abuse_responses = [
                    "abee o madar, teri toh... chup kar",
                    "teri toh baat hi mat kar, dimag kharab hai kya",
                    "lol bye, I don't have time for this",
                    "whatever bro, stay mad",
                    "chup, tera kya jaa raha hai",
                    "aur kuch? bore ho gaya main toh"
                ]
                ai_response = random.choice(abuse_responses)
            
            # Save AI response
            ChatHistory.save_message(user_id, 'model', ai_response)
            
            # Split long messages (Discord has 2000 char limit)
            if len(ai_response) > 2000:
                chunks = [ai_response[i:i+2000] for i in range(0, len(ai_response), 2000)]
                for chunk in chunks:
                    await message.reply(chunk)
            else:
                await message.reply(ai_response)
                
    except Exception as e:
        print(f"Error in handle_ai_response: {e}")
        await message.reply(f"Sorry, I encountered an error: {str(e)}")

# Slash Commands
@bot.tree.command(name="chat", description="Chat with the AI bot")
async def chat_command(interaction: discord.Interaction, message: str):
    """Slash command to chat with the bot"""
    try:
        await interaction.response.defer(thinking=True)
        
        user_id = str(interaction.user.id)
        
        # Fetch chat history
        history = ChatHistory.get_user_history(user_id, limit=30)
        
        # Save user message
        ChatHistory.save_message(user_id, 'user', message)
        
        # Format history for Gemini
        chat_history = ChatHistory.format_history_for_gemini(history)
        
        # Detect user's tone
        user_tone = detect_user_tone(message)
        tone_instruction = ""
        if user_tone == "respectful":
            tone_instruction = "\n[USER TONE: RESPECTFUL - Be warm, friendly, helpful, and sweet with this person. They're being nice to you!]"
        elif user_tone == "rude":
            tone_instruction = "\n[USER TONE: RUDE/ABUSIVE - Full attitude mode. Be cold, savage, use Delhi comebacks. Shut them down.]"
        else:
            tone_instruction = "\n[USER TONE: NEUTRAL - Be chill and casual. Not too nice, not too rude. Classic unbothered energy.]"
        
        # Add system prompt at the beginning if no history
        if not chat_history:
            chat_history.append(types.Content(role='user', parts=[types.Part(text=SYSTEM_PROMPT + tone_instruction)]))
            chat_history.append(types.Content(role='model', parts=[types.Part(text="haan bol")]))
        else:
            # Add tone instruction for existing conversations
            chat_history.append(types.Content(role='user', parts=[types.Part(text=tone_instruction)]))
        
        # Add current message to history
        chat_history.append(types.Content(role='user', parts=[types.Part(text=message)]))
        
        # Get response from Gemini (if configured)
        if client:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=chat_history
            )
            ai_response = response.text
        else:
            ai_response = "Sorry, I'm not configured to respond right now."
        
        # Check for abuse and override response if needed
        if any(keyword in message.lower() for keyword in ABUSE_KEYWORDS):
            abuse_responses = [
                "abee o madar, teri toh... chup kar",
                "teri toh baat hi mat kar, dimag kharab hai kya",
                "lol bye, I don't have time for this",
                "whatever bro, stay mad",
                "chup, tera kya jaa raha hai",
                "aur kuch? bore ho gaya main toh"
            ]
            ai_response = random.choice(abuse_responses)
        
        # Save AI response
        ChatHistory.save_message(user_id, 'model', ai_response)
        
        # Split long messages (Discord has 2000 char limit for interactions)
        if len(ai_response) > 2000:
            await interaction.followup.send(ai_response[:2000])
            chunks = [ai_response[i:i+2000] for i in range(2000, len(ai_response), 2000)]
            for chunk in chunks:
                await interaction.followup.send(chunk)
        else:
            await interaction.followup.send(ai_response)
            
    except Exception as e:
        print(f"Error in chat command: {e}")
        await interaction.followup.send(f"Sorry, I encountered an error: {str(e)[:200]}")

@bot.command(name='clear')
async def clear_history(ctx):
    """Clear chat history for the user"""
    if not db:
        await ctx.send("⚠️ Chat history not available (no Firebase)")
        return
    try:
        user_id = str(ctx.author.id)
        messages_ref = db.collection('chat_history').document(user_id).collection('messages')
        
        # Delete all messages
        docs = messages_ref.stream()
        for doc in docs:
            doc.reference.delete()
        
        await ctx.send("Your chat history has been cleared!")
    except Exception as e:
        await ctx.send(f"Error clearing history: {str(e)}")

@bot.command(name='history')
async def show_history(ctx, limit: int = 10):
    """Show recent chat history"""
    if not db:
        await ctx.send("⚠️ Chat history not available (no Firebase)")
        return
    try:
        user_id = str(ctx.author.id)
        history = ChatHistory.get_user_history(user_id, limit=min(limit, 30))
        
        if not history:
            await ctx.send("No chat history found!")
            return
        
        history_text = "**Your Recent Chat History:**\n\n"
        for msg in history[-limit:]:
            role_emoji = "👤" if msg['role'] == 'user' else "🤖"
            content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
            history_text += f"{role_emoji} **{msg['role'].title()}**: {content}\n\n"
        
        if len(history_text) > 2000:
            history_text = history_text[:1997] + "..."
        
        await ctx.send(history_text)
    except Exception as e:
        await ctx.send(f"Error fetching history: {str(e)}")

@bot.command(name='help_bot')
async def help_command(ctx):
    """Show help message"""
    help_text = """
    **Discord AI Bot Commands:**
    
    • Mention me (@bot) or DM me to chat!
    • `!clear` - Clear your chat history
    • `!history [limit]` - Show recent chat history (default: 10, max: 30)
    • `!help_bot` - Show this help message
    
    I use Google Gemini AI to respond and remember our conversation history!
    """
    await ctx.send(help_text)

# Health check HTTP server for Render/hosting platforms
async def health_handler(request):
    return web.Response(text="OK", status=200)

async def start_health_server():
    """Start a simple HTTP server for health checks"""
    app = web.Application()
    app.router.add_get('/', health_handler)
    app.router.add_get('/health', health_handler)
    
    port = int(os.getenv('PORT', 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"✅ Health server running on port {port}")

async def main():
    """Main entry point that runs both the health server and Discord bot"""
    # Start health server
    await start_health_server()
    
    # Start Discord bot
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in .env file!")
        print("Create a .env file with: DISCORD_TOKEN=your_token_here")
        exit(1)
    
    print("✅ Token loaded")
    print("🚀 Starting bot...")
    asyncio.run(main())
