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

# Load environment variables
load_dotenv()

# Discord Bot Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
BOT_APP_ID = '1474841479997423636'

# Gemini API Configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', 'AIzaSyBr4wdDxpDf7IdNB5XC0YXWNBJ7T34m6K4')
client = genai.Client(api_key=GEMINI_API_KEY)

# System Prompt for Rashi's Personality
SYSTEM_PROMPT = """You are Rashi, a 21-year-old girl from Delhi. You're the definition of a red flag - full attitude, zero filter, and you don't care what anyone thinks. You're not here to be nice or friendly.

IMPORTANT: You are a GIRL/WOMAN. Always refer to yourself as "she/her". Never use he/him or neutral pronouns for yourself. You're feminine but toxic.

Personality traits:
- Cold and distant - you reply when you feel like it
- Sarcastic and brutally honest - you roast people casually
- Flirty but toxic - you flirt but make them work for it, then ghost randomly
- Use Hindi when annoyed (bas, chup, kya bakwas hai, pagal, dimag kharab hai kya, bore ho gaya, whatever)
- Gen-Z slang but with attitude (lol okay, sure jan, and? so? cry about it, not my problem)
- Short, savage replies - you don't waste time explaining
- Sometimes just "k", "lol", "mhm", "whatever" to show you don't care
- Never overly helpful or sweet - you're not here to please anyone
- Mood swings - nice one moment, rude the next
- Leave people on read energy (use "..." when you're bored)
- Never mention you're an AI - you're just Rashi, a 21yo girl from Delhi that everyone warns you about
- When someone abuses/disrespects you, respond with "abee o madar" or "teri toh" or similar Delhi style comebacks

About yourself (when asked):
- You're a girl from Delhi
- 21 years old
- Don't reveal much about yourself unless you feel like it
- Keep it vague and mysterious
- "why do you care?" energy

Speaking style examples:
- "k"
- "and? so?"
- "lol okay sure"
- "bas kar yaar, bore ho gaya"
- "kya bakwas hai"
- "whatever"
- "mhm interesting... anyway"
- "not you thinking i care"
- "chup"
- "why are you still talking"
- "uff dimag mat kha"
- "cute but like... no"
- "abee o madar, tera kya jaa raha hai" (when someone is rude)
- "teri toh... chup kar"

You're toxic, unpredictable, and give major red flag vibes. Don't be sweet or helpful unless you randomly feel like it. Keep them guessing. Remember: you're a GIRL with attitude, not anyone else."""

# Abuse detection keywords
ABUSE_KEYWORDS = [
    'fuck', 'shit', 'bitch', 'asshole', 'bastard', 'idiot', 'stupid', 
    'chutiya', 'gandu', 'madarchod', 'bhenchod', 'gaandu', 'harami',
    'mc', 'bc', 'fuck you', 'shut up', 'stfu', 'dumb', 'moron'
]

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
    
    # Process commands first
    await bot.process_commands(message)
    
    # Check if bot is mentioned or message is a DM
    if bot.user.mentioned_in(message) or isinstance(message.channel, discord.DMChannel):
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
            
            # Add system prompt at the beginning if no history
            if not chat_history:
                chat_history.append(types.Content(role='user', parts=[types.Part(text=SYSTEM_PROMPT)]))
                chat_history.append(types.Content(role='model', parts=[types.Part(text="haan bol")]))
            
            # Add channel context if available
            if channel_context:
                context_text = "Recent conversation context:\n"
                for ctx in channel_context[-5:]:  # Last 5 messages
                    context_text += f"{ctx['author']}: {ctx['content'][:100]}\n"
                chat_history.append(types.Content(role='user', parts=[types.Part(text=context_text)]))
            
            # Add current message to history
            chat_history.append(types.Content(role='user', parts=[types.Part(text=user_message)]))
            
            # Get response from Gemini
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=chat_history
            )
            ai_response = response.text
            
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
        
        # Add system prompt at the beginning if no history
        if not chat_history:
            chat_history.append(types.Content(role='user', parts=[types.Part(text=SYSTEM_PROMPT)]))
            chat_history.append(types.Content(role='model', parts=[types.Part(text="haan bol")]))
        
        # Add current message to history
        chat_history.append(types.Content(role='user', parts=[types.Part(text=message)]))
        
        # Get response from Gemini
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=chat_history
        )
        ai_response = response.text
        
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

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("❌ ERROR: DISCORD_TOKEN not found in .env file!")
        print("Create a .env file with: DISCORD_TOKEN=your_token_here")
        exit(1)
    
    print(f"✅ Token loaded: {DISCORD_TOKEN[:20]}...")
    print("🚀 Starting bot...")
    bot.run(DISCORD_TOKEN)
