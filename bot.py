import logging
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import openai
import requests
from openai.error import RateLimitError, InvalidRequestError
import psycopg2
import os
import json
import PyPDF2
from bs4 import BeautifulSoup
from googleapiclient.discovery import build

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API Keys
openai.api_key = os.getenv('OPENAI_API_KEY')
news_api_key = os.getenv('NEWS_API_KEY')
weather_api_key = os.getenv('WEATHER_API_KEY')
oxford_api_key = os.getenv('OXFORD_API_KEY')
oxford_app_id = os.getenv('OXFORD_APP_ID')
youtube_api_key = os.getenv('YOUTUBE_API_KEY')
listennotes_api_key = os.getenv('LISTEN_API_KEY')

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL, sslmode='require')

# Dictionary to store conversation history
user_conversations = {}

# Define the start command handler
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_conversations[user_id] = [{"role": "system", "content": "You are a friendly and engaging assistant. Respond like a friend and keep the conversation light and fun."}]
    await update.message.reply_text('Hey there! I’m your friendly chat bot. What’s up?')
    
    # Notify the admin about a new user
    admin_id = 953090755  # Your Telegram ID
    await context.bot.send_message(admin_id, f"New user started a chat: {user_id}")

# Define the news command handler
async def news(update: Update, context: CallbackContext) -> None:
    url = f'https://newsapi.org/v2/top-headlines?country=us&apiKey={news_api_key}'
    response = requests.get(url)
    if response.status_code == 200:
        articles = response.json().get('articles', [])
        if articles:
            news_message = '\n\n'.join([f"{article['title']} - {article['source']['name']}" for article in articles[:5]])
            await update.message.reply_text(news_message)
        else:
            await update.message.reply_text("No news articles found.")
    else:
        await update.message.reply_text("Failed to fetch news.")

# Define the weather command handler
async def weather(update: Update, context: CallbackContext) -> None:
    location = ' '.join(context.args)
    if not location:
        await update.message.reply_text("Please provide a location.")
        return
    url = f'http://api.openweathermap.org/data/2.5/weather?q={location}&appid={weather_api_key}&units=metric'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        weather_message = (f"Weather in {data['name']}:\n"
                           f"Temperature: {data['main']['temp']}°C\n"
                           f"Weather: {data['weather'][0]['description']}\n"
                           f"Humidity: {data['main']['humidity']}%\n"
                           f"Wind Speed: {data['wind']['speed']} m/s")
        await update.message.reply_text(weather_message)
    else:
        await update.message.reply_text("Failed to fetch weather information. Please check the location.")

# Define the joke command handler
async def joke(update: Update, context: CallbackContext) -> None:
    url = 'https://v2.jokeapi.dev/joke/Any'
    response = requests.get(url)
    if response.status_code == 200:
        joke_data = response.json()
        if joke_data['type'] == 'single':
            joke_text = joke_data['joke']
        else:
            joke_text = f"{joke_data['setup']} ... {joke_data['delivery']}"
        await update.message.reply_text(joke_text)
    else:
        await update.message.reply_text("Failed to fetch a joke.")

# Define the define command handler
async def define(update: Update, context: CallbackContext) -> None:
    word = ' '.join(context.args)
    if not word:
        await update.message.reply_text("Please provide a word to define.")
        return
    url = f"https://od-api.oxforddictionaries.com/api/v2/entries/en-gb/{word.lower()}"
    headers = {
        "app_id": oxford_app_id,
        "app_key": oxford_api_key
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        definitions = response.json().get('results', [])[0].get('lexicalEntries', [])[0].get('entries', [])[0].get('senses', [])[0].get('definitions', [])
        if definitions:
            await update.message.reply_text(f"Definition of {word}: {definitions[0]}")
        else:
            await update.message.reply_text(f"No definitions found for {word}.")
    else:
        await update.message.reply_text(f"Failed to fetch definition for {word}.")

# Define the YouTube search command handler
async def youtube(update: Update, context: CallbackContext) -> None:
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Please provide a search query.")
        return
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    request = youtube.search().list(part='snippet', q=query, maxResults=5)
    response = request.execute()
    videos = response.get('items', [])
    if videos:
        video_links = [f"https://www.youtube.com/watch?v={video['id']['videoId']}" for video in videos if video['id']['kind'] == 'youtube#video']
        await update.message.reply_text('\n'.join(video_links))
    else:
        await update.message.reply_text("No videos found.")

# Define the podcast search command handler
async def podcast(update: Update, context: CallbackContext) -> None:
    query = ' '.join(context.args)
    if not query:
        await update.message.reply_text("Please provide a search query.")
        return
    url = f'https://listen-api.listennotes.com/api/v2/search?q={query}&sort_by_date=0&len_min=0&len_max=9999&episode_count_min=0&episode_count_max=9999&language=English&safe_mode=0'
    headers = {'X-ListenAPI-Key': listennotes_api_key}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        podcasts = response.json().get('results', [])
        if podcasts:
            podcast_links = [podcast['link'] for podcast in podcasts[:5]]
            await update.message.reply_text('\n'.join(podcast_links))
        else:
            await update.message.reply_text("No podcasts found.")
    else:
        await update.message.reply_text("Failed to fetch podcasts.")

# Define the message handler
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_message = update.message.text.lower()

    # Ensure the user has a conversation history
    if user_id not in user_conversations:
        user_conversations[user_id] = [{"role": "system", "content": "You are a friendly and engaging assistant. Respond like a friend and keep the conversation light and fun."}]
    
    # Append the user's message to the conversation history
    user_conversations[user_id].append({"role": "user", "content": user_message})

    # Detect keywords and respond accordingly
    if "news" in user_message:
        await news(update, context)
    elif "weather" in user_message:
        await weather(update, context)
    elif "joke" in user_message:
        await joke(update, context)
    elif "define" in user_message:
        await define(update, context)
    elif "youtube" in user_message:
        await youtube(update, context)
    elif "podcast" in user_message:
        await podcast(update, context)
    elif "read pdf" in user_message:
        await read_pdf(update, context)
    elif "scrape website" in user_message:
        await scrape_website(update, context)
    elif "quiz" in user_message:
        await quiz(update, context)
    else:
        try:
            # Send Message to OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=user_conversations[user_id]
            )

            # Get the assistant's response
            assistant_message = response.choices[0].message['content'].strip()

            # Append the assistant's response to the conversation history
            user_conversations[user_id].append({"role": "assistant", "content": assistant_message})

            # Store the conversation in the database
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM user_conversations WHERE user_id = %s", (user_id,))
                if cur.fetchone()[0] > 0:
                    cur.execute("UPDATE user_conversations SET conversation = %s WHERE user_id = %s", (json.dumps(user_conversations[user_id]), user_id))
                else:
                    cur.execute("INSERT INTO user_conversations (user_id, conversation) VALUES (%s, %s)", (user_id, json.dumps(user_conversations[user_id])))
                conn.commit()

            # Reply with the GPT-3.5 Response
            await update.message.reply_text(assistant_message)
        
        except RateLimitError:
            await update.message.reply_text("I have reached my usage limit for now. Please try again later.")
        except InvalidRequestError as e:
            if 'insufficient_quota' in str(e):
                await update.message.reply_text("I have reached my usage limit for now. Please try again later.")
            else:
                await update.message.reply_text(f"An error occurred: {e}")


# Define the view chats command handler
async def view_chats(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id != 953090755:  # Your Telegram user ID
        await update.message.reply_text("You are not authorized to use this command.")
        return

    # Fetch chat history from the database
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cur = conn.cursor()
        cur.execute("SELECT user_id, conversation FROM user_conversations")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if rows:
            for row in rows:
                chat_user_id, conversation = row
                conversation_data = json.loads(conversation)
                conversation_text = f"User ID: {chat_user_id}\n\n"
                for message in conversation_data:
                    conversation_text += f"{message['role']}: {message['content']}\n"
                await update.message.reply_text(conversation_text)
        else:
            await update.message.reply_text("No conversation history found.")

    except Exception as e:
        logger.error(f"Error fetching conversation history: {e}")
        await update.message.reply_text("An error occurred while fetching conversation history.")

# Define the PDF reader handler
async def read_pdf(update: Update, context: CallbackContext) -> None:
    if not update.message.document:
        await update.message.reply_text("Please send a PDF document.")
        return

    file = await context.bot.get_file(update.message.document.file_id)
    file_path = "temp.pdf"
    await file.download_to_drive(file_path)

    try:
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text()
            user_id = update.message.from_user.id
            context.user_data['pdf_text'] = text
            await update.message.reply_text("PDF text extracted. You can now quiz yourself by using the keyword 'quiz'.")
    except Exception as e:
        logger.error(f"Error reading PDF: {e}")
        await update.message.reply_text("An error occurred while reading the PDF.")
    finally:
        os.remove(file_path)

# Define the web scraper handler
async def scrape_website(update: Update, context: CallbackContext) -> None:
    url = ' '.join(context.args)
    if not url:
        await update.message.reply_text("Please provide a URL.")
        return

    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            text = soup.get_text()
            await update.message.reply_text(text[:4096])  # Telegram message limit
        else:
            await update.message.reply_text("Failed to fetch the website.")
    except Exception as e:
        logger.error(f"Error scraping website: {e}")
        await update.message.reply_text("An error occurred while scraping the website.")

# Define the quiz command handler
async def quiz(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if 'pdf_text' not in context.user_data:
        await update.message.reply_text("Please upload a PDF first.")
        return
    
    pdf_text = context.user_data['pdf_text']

    # Generate questions using OpenAI
    prompt = f"Generate 5 quiz questions from the following text:\n\n{pdf_text}"
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": "Generate 5 quiz questions from the following text."}, {"role": "user", "content": pdf_text}]
        )
        questions = response.choices[0].message['content'].strip()
        context.user_data['quiz_questions'] = questions
        await update.message.reply_text(f"Here are your quiz questions:\n\n{questions}")
    except Exception as e:
        logger.error(f"Error generating quiz questions: {e}")
        await update.message.reply_text("An error occurred while generating quiz questions.")

# Main function to start the bot
def main() -> None:
    telegram_bot_token = os.getenv('TELEGRAM_BOT_TOKEN')

    # Create the Application and pass it your bot's token.
    application = Application.builder().token(telegram_bot_token).build()

    # Register the start command handler.
    application.add_handler(CommandHandler("start", start))

    # Register the news command handler.
    application.add_handler(CommandHandler("news", news))

    # Register the weather command handler.
    application.add_handler(CommandHandler("weather", weather))

    # Register the joke command handler.
    application.add_handler(CommandHandler("joke", joke))

    # Register the define command handler.
    application.add_handler(CommandHandler("define", define))

    # Register the YouTube search command handler.
    application.add_handler(CommandHandler("youtube", youtube))

    # Register the podcast search command handler.
    application.add_handler(CommandHandler("podcast", podcast))

    # Register the view chats command handler.
    application.add_handler(CommandHandler("view_chats", view_chats))

    # Register the PDF reader command handler.
    application.add_handler(CommandHandler("read_pdf", read_pdf))

    # Register the quiz command handler.
    application.add_handler(CommandHandler("quiz", quiz))

    # Register the web scraper command handler.
    application.add_handler(CommandHandler("scrape_website", scrape_website))

    # Register the message handler.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Register the document handler for PDFs.
    application.add_handler(MessageHandler(filters.Document.PDF, read_pdf))

    # Start the bot.
    application.run_polling()

if __name__ == '__main__':
    main()
