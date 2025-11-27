# import speech_recognition as sr
# import pyttsx3
# import requests
# import wikipedia
# import subprocess
# import sys
# import time

# # --- Setup text-to-speech engine ---
# engine = pyttsx3.init()
# def speak(text):
#     engine.say(text)
#     engine.runAndWait()

# # --- Speech to Text ---
# def listen():
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         print("Listening... Please speak now.")
#         recognizer.adjust_for_ambient_noise(source, duration=0.5)
#         audio = recognizer.listen(source, phrase_time_limit=7)
#     try:
#         command = recognizer.recognize_google(audio)
#         print(f"You said: {command}")
#         return command.lower()
#     except sr.UnknownValueError:
#         speak("Sorry, I did not catch that.")
#         return ""
#     except sr.RequestError:
#         speak("Sorry, my speech service is down.")
#         return ""

# # --- Launch an app on your PC (Windows example) ---
# def launch_app(app_name):
#     apps = {
#         "notepad": r"C:\Windows\System32\notepad.exe",
#         "calculator": r"C:\Windows\System32\calc.exe",
#         # Add more apps and paths here
#     }
#     path = apps.get(app_name)
#     if path:
#         subprocess.Popen([path])
#         speak(f"Launching {app_name}")
#     else:
#         speak(f"Sorry, I don't know how to open {app_name}")

# # --- Get latest news headlines ---
# def get_news():
#     API_KEY = "5300c5c9353c47f2b9c86037dc4b721a"   # Your NewsAPI key
#     url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={API_KEY}"
#     try:
#         response = requests.get(url)
#         articles = response.json().get("articles", [])[:3]
#         if not articles:
#             speak("Sorry, no news found.")
#             return
#         speak("Here are the top news headlines.")
#         for i, article in enumerate(articles, 1):
#             headline = article['title']
#             speak(f"Headline {i}: {headline}")
#             print(f"{i}. {headline}")
#             time.sleep(1)
#     except Exception as e:
#         speak("Sorry, I am unable to fetch news right now.")
#         print("News error:", e)

# # --- Get weather using Open-Meteo (no API key required) ---
# def get_weather(location):
#     cities = {
#         "mumbai": (19.0760, 72.8777),
#         "delhi": (28.7041, 77.1025),
#         "bangalore": (12.9716, 77.5946),
#         "chennai": (13.0827, 80.2707),
#         # add more cities here
#     }
#     coords = cities.get(location.lower())
#     if not coords:
#         speak(f"Sorry, I don't have data for {location}. Please try Mumbai, Delhi, Bangalore, or Chennai.")
#         return
#     lat, lon = coords
#     url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
#     try:
#         resp = requests.get(url)
#         data = resp.json()
#         weather = data['current_weather']
#         temp = weather['temperature']
#         wind = weather['windspeed']
#         speak(f"The current temperature in {location} is {temp} degrees Celsius with wind speed {wind} kilometers per hour.")
#         print(f"Temperature: {temp}°C, Windspeed: {wind} km/h")
#     except Exception as e:
#         speak("Sorry, I can't get weather data right now.")
#         print("Weather error:", e)

# # --- Get stock price from Marketstack ---
# def get_stock_price(stock_symbol):
#     API_KEY = "dab5f7ef7c04eea7b42adffb6d9e3790"   # Your Marketstack API key
#     url = f"http://api.marketstack.com/v1/eod?access_key={API_KEY}&symbols={stock_symbol.upper()}"
#     try:
#         response = requests.get(url)
#         data = response.json()
#         if 'data' not in data or not data['data']:
#             speak(f"Sorry, I couldn't find data for stock {stock_symbol}")
#             return
#         latest = data['data'][0]
#         close_price = latest['close']
#         speak(f"The latest closing price of {stock_symbol.upper()} is {close_price} dollars.")
#         print(f"{stock_symbol.upper()} close price: {close_price}")
#     except Exception as e:
#         speak("Sorry, I am unable to fetch stock data right now.")
#         print("Stock error:", e)

# # --- Wikipedia summary for general knowledge ---
# def get_wikipedia_summary(topic):
#     try:
#         summary = wikipedia.summary(topic, sentences=2)
#         speak(summary)
#         print(summary)
#     except wikipedia.DisambiguationError as e:
#         speak(f"Your query is ambiguous. Did you mean: {e.options[0]}?")
#     except Exception as e:
#         speak("Sorry, I couldn't find information on that topic.")
#         print("Wiki error:", e)

# # --- Simple intent detection --- 
# def parse_command(command):
#     if not command:
#         return None, None

#     if 'news' in command:
#         return 'news', None
#     elif 'weather' in command:
#         words = command.split()
#         if 'in' in words:
#             loc_index = words.index('in')
#             if loc_index + 1 < len(words):
#                 location = words[loc_index + 1]
#                 return 'weather', location
#         return 'weather', 'mumbai'
#     elif 'stock' in command or 'market' in command:
#         words = command.split()
#         symbols_words = ['stock', 'price', 'market']
#         for i, word in enumerate(words):
#             if word in symbols_words and i + 1 < len(words):
#                 return 'stock', words[i + 1].upper()
#         return 'stock', 'AAPL'
#     elif 'open' in command:
#         words = command.split()
#         if 'open' in words:
#             app_index = words.index('open')
#             if app_index + 1 < len(words):
#                 app_name = words[app_index + 1]
#                 return 'open_app', app_name
#         return 'open_app', None
#     elif 'who is' in command or 'what is' in command:
#         topic = command.replace('who is', '').replace('what is', '').strip()
#         return 'wikipedia', topic
#     else:
#         return 'unknown', None

# # --- Main AI assistant loop ---
# def main():
#     speak("Hello! I am your AI assistant. How can I help you today?")
#     while True:
#         command = listen()
#         if command in ['exit', 'quit', 'stop', 'bye']:
#             speak("Goodbye! Have a nice day.")
#             sys.exit(0)

#         intent, param = parse_command(command)

#         if intent == 'news':
#             get_news()
#         elif intent == 'weather':
#             if param:
#                 get_weather(param)
#             else:
#                 speak("Please tell me the location for the weather.")
#         elif intent == 'stock':
#             if param:
#                 get_stock_price(param)
#             else:
#                 speak("Please specify the stock symbol.")
#         elif intent == 'open_app':
#             if param:
#                 launch_app(param)
#             else:
#                 speak("Please specify the app you want me to open.")
#         elif intent == 'wikipedia':
#             if param:
#                 get_wikipedia_summary(param)
#             else:
#                 speak("Please tell me what you want to know.")
#         else:
#             speak("Sorry, I did not understand that. Please try again.")

# if __name__ == "__main__":
#     main()
#//////////////////////////////new code 1#######

# import speech_recognition as sr
# import pyttsx3
# import requests
# import wikipedia
# import subprocess
# import sys
# import time
# import random

# # ---- CONFIGURATION ----
# NEWS_API_KEY = "5300c5c9353c47f2b9c86037dc4b721a"
# MARKETSTACK_KEY = "dab5f7ef7c04eea7b42adffb6d9e3790"

# CITIES = {
#     "mumbai": (19.0760, 72.8777),
#     "delhi": (28.7041, 77.1025),
#     "bangalore": (12.9716, 77.5946),
#     "chennai": (13.0827, 80.2707),
# }

# APPS = {
#     "notepad": r"C:\Windows\System32\notepad.exe",
#     "calculator": r"C:\Windows\System32\calc.exe",
#     "edge": r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
#     "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe",

#     # Add more here
# }

# FALLBACK_RESPONSES = [
#     "Sorry, I didn't quite catch that. Could you try again?",
#     "Hmm, that one's a mystery. Can you say it differently?",
#     "Oops! I'm not programmed for that yet, but I'm learning every day!"
# ]

# # ---- VOICE ENGINE ----
# engine = pyttsx3.init()

# def speak(text, show=True):
#     if show:
#         print(f"💬: {text}")
#     engine.say(text)
#     engine.runAndWait()

# def get_voice_command():
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         speak(random.choice([
#             "Listening now. What's your wish?",
#             "Go ahead, I'm all ears!",
#             "Ready for your command."
#         ]), show=False)
#         audio = recognizer.listen(source, phrase_time_limit=7)
#     try:
#         return recognizer.recognize_google(audio).lower()
#     except sr.UnknownValueError:
#         speak("I heard nothing. Can you repeat?")
#         return ""
#     except sr.RequestError:
#         speak("Sorry, my speech system is having issues.")
#         return ""

# # ---- FEATURES ----
# def launch_app(app_name):
#     if app_name in APPS:
#         subprocess.Popen([APPS[app_name]])
#         speak(f"Opening {app_name.capitalize()} for you! 🚀")
#     else:
#         speak("App not found. You can add it in my code if you like!")

# def get_news():
#     url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"
#     try:
#         response = requests.get(url)
#         articles = response.json().get("articles", [])[:3]
#         if not articles:
#             speak("No news right now. The world must be sleeping!")
#             return
#         speak("Here's what's hot in the news headlines:")
#         for i, article in enumerate(articles, 1):
#             headline = article['title']
#             speak(f"Headline {i}: {headline}")
#     except Exception:
#         speak("News service isn't responding. Let's try later.")

# def get_weather(location):
#     coords = CITIES.get(location)
#     if not coords:
#         speak("Don't know that city yet. Try Mumbai, Delhi, Bangalore or Chennai.")
#         return
#     lat, lon = coords
#     url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
#     try:
#         resp = requests.get(url)
#         data = resp.json()
#         weather = data['current_weather']
#         speak(f"It's {weather['temperature']}°C in {location.capitalize()} with winds at {weather['windspeed']} kph.")
#     except Exception:
#         speak("Weather lookup failed. Storm in the API, maybe?")

# def get_stock(stock_symbol):
#     url = f"http://api.marketstack.com/v1/eod?access_key={MARKETSTACK_KEY}&symbols={stock_symbol.upper()}"
#     try:
#         response = requests.get(url)
#         data = response.json()
#         if 'data' not in data or not data['data']:
#             speak("Stock not found. Are you sure that's the symbol?")
#             return
#         latest = data['data'][0]
#         speak(f"{stock_symbol.upper()}'s latest close: {latest['close']} dollars.")
#     except Exception:
#         speak("Stocks server not working. Wall Street is taking a nap.")

# def get_wikipedia_summary(topic):
#     try:
#         summary = wikipedia.summary(topic, sentences=2)
#         speak(summary)
#     except wikipedia.DisambiguationError as e:
#         speak(f"That's ambiguous. Did you mean {e.options[0]}?")
#     except Exception:
#         speak("Wikipedia's in the dark on that one!")

# def tell_joke():
#     jokes = [
#         "Why do Java developers wear glasses? Because they don't see sharp!",
#         "Why did the robot go on vacation? To recharge its batteries!",
#         "I would tell you a UDP joke, but you might not get it."
#     ]
#     speak(random.choice(jokes))

# # ---- INTENT PARSER ----
# def parse_command(cmd):
#     cmd = cmd.lower()
#     if 'joke' in cmd:
#         return 'joke', None
#     if 'news' in cmd:
#         return 'news', None
#     if 'weather' in cmd or 'temperature' in cmd:
#         for city in CITIES:
#             if city in cmd:
#                 return 'weather', city
#         return 'weather', 'mumbai'
#     if 'stock' in cmd or 'market' in cmd or 'price' in cmd:
#         parts = cmd.split()
#         for idx, word in enumerate(parts):
#             if word in ['stock', 'price', 'market'] and idx+1 < len(parts):
#                 return 'stock', parts[idx+1]
#         return 'stock', 'AAPL'
#     if 'open' in cmd:
#         for app in APPS:
#             if app in cmd:
#                 return 'open_app', app
#         return 'open_app', None
#     if 'who is' in cmd or 'what is' in cmd:
#         topic = cmd.replace('who is', '').replace('what is', '').strip()
#         return 'wikipedia', topic
#     if cmd in ['exit', 'quit', 'stop', 'bye']:
#         return 'exit', None
#     return 'fallback', None

# # ---- MAIN LOOP ----
# def main():
#     speak("Hi there! This is your new stylish AI. Ask me for news, weather, stocks, a joke, or to open apps. Say 'exit' to quit.")
#     while True:
#         cmd = get_voice_command()
#         intent, arg = parse_command(cmd)
#         if intent == 'news':
#             get_news()
#         elif intent == 'weather':
#             get_weather(arg)
#         elif intent == 'stock':
#             get_stock(arg)
#         elif intent == 'open_app':
#             if arg:
#                 launch_app(arg)
#             else:
#                 speak("Tell me what app to open!")
#         elif intent == 'wikipedia':
#             get_wikipedia_summary(arg)
#         elif intent == 'joke':
#             tell_joke()
#         elif intent == 'exit':
#             speak("Signing off with style. Stay awesome!")
#             sys.exit(0)
#         else:
#             speak(random.choice(FALLBACK_RESPONSES))

# if __name__ == "__main__":
#     main()
#------------------------------------------------------------------------------------------------------------#
# import speech_recognition as sr
# import pyttsx3
# import requests
# import wikipedia
# import subprocess
# import sys
# import time
# import random
# import os
# import json
# from difflib import get_close_matches

# # For shortcut resolving
# import pythoncom
# from win32com.shell import shell, shellcon

# # ---- CONFIGURATION ----

# NEWS_API_KEY = "5300c5c9353c47f2b9c86037dc4b721a"
# MARKETSTACK_KEY = "dab5f7ef7c04eea7b42adffb6d9e3790"

# CITIES = {
#     "mumbai": (19.0760, 72.8777),
#     "delhi": (28.7041, 77.1025),
#     "bangalore": (12.9716, 77.5946),
#     "chennai": (13.0827, 80.2707),
#     # Add more cities if required
# }

# APP_INDEX_FILE = "apps.json"

# # ---- VOICE ENGINE ----
# engine = pyttsx3.init()

# def speak(text, show=True):
#     if show:
#         print(f"💬: {text}")
#     engine.say(text)
#     engine.runAndWait()

# def get_voice_command():
#     recognizer = sr.Recognizer()
#     with sr.Microphone() as source:
#         speak(random.choice([
#             "Listening now. What's your wish?",
#             "Go ahead, I'm all ears!",
#             "Ready for your command."
#         ]), show=False)
#         recognizer.adjust_for_ambient_noise(source, duration=0.5)
#         audio = recognizer.listen(source, phrase_time_limit=7)
#     try:
#         return recognizer.recognize_google(audio).lower()
#     except sr.UnknownValueError:
#         speak("I heard nothing. Can you repeat?")
#         return ""
#     except sr.RequestError:
#         speak("Sorry, my speech system is having issues.")
#         return ""

# # --- Shortcut resolver for .lnk files ---
# def resolve_shortcut(lnk_path):
#     try:
#         shell_link = pythoncom.CoCreateInstance(
#             shell.CLSID_ShellLink, None,
#             pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
#         persist_file = shell_link.QueryInterface(pythoncom.IID_IPersistFile)
#         persist_file.Load(lnk_path)
#         path, _ = shell_link.GetPath(shell.SLGP_RAWPATH)
#         return path
#     except Exception as e:
#         print(f"Failed to resolve shortcut {lnk_path}: {e}")
#         return lnk_path

# # ---- Application Indexing and Launching ----
# def load_or_build_app_index():
#     """
#     Build or load the app index mapping app names to executable paths.
#     Walks common installation and start menu folders for .lnk and .exe files.
#     """
#     if not os.path.exists(APP_INDEX_FILE):
#         search_dirs = [
#             r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
#             os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
#             r"C:\Program Files",
#             r"C:\Program Files (x86)",
#             r"C:\Windows\System32"
#         ]
#         app_paths = {}
#         for root_dir in search_dirs:
#             if not root_dir or not os.path.exists(root_dir):
#                 continue
#             for root, _, files in os.walk(root_dir):
#                 for file in files:
#                     if file.lower().endswith(('.lnk', '.exe')):
#                         name = os.path.splitext(file)[0].lower()
#                         if name not in app_paths:
#                             path = os.path.join(root, file)
#                             app_paths[name] = path
#         with open(APP_INDEX_FILE, "w") as f:
#             json.dump(app_paths, f)
#         print(f"Indexed {len(app_paths)} applications.")
#         return app_paths
#     else:
#         with open(APP_INDEX_FILE, "r") as f:
#             return json.load(f)

# def launch_app(app_name):
#     apps = load_or_build_app_index()
#     app_name = app_name.lower().strip()

#     if app_name in apps:
#         app_path = apps[app_name]
#         if app_path.lower().endswith('.lnk'):
#             app_path = resolve_shortcut(app_path)
#         try:
#             subprocess.Popen(app_path)
#             speak(f"Opening {app_name.capitalize()} for you!")
#         except Exception as e:
#             speak(f"Sorry, I could not open {app_name} due to an error.")
#             print(f"Error launching {app_name}: {e}")
#         return

#     # Use fuzzy match if exact app name not found
#     match = get_close_matches(app_name, apps.keys(), n=1, cutoff=0.6)
#     if match:
#         real_app = match[0]
#         app_path = apps[real_app]
#         if app_path.lower().endswith('.lnk'):
#             app_path = resolve_shortcut(app_path)
#         try:
#             subprocess.Popen(app_path)
#             speak(f"I think you meant {real_app.capitalize()}. Opening it now!")
#         except Exception as e:
#             speak(f"Sorry, I could not open {real_app} due to an error.")
#             print(f"Error launching {real_app}: {e}")
#     else:
#         speak("Couldn't find that app. Try a different name or say 'reindex' to update app list.")


# # ---- FEATURES ----

# def get_news():
#     url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"
#     try:
#         response = requests.get(url)
#         articles = response.json().get("articles", [])[:3]
#         if not articles:
#             speak("No news available at the moment.")
#             return
#         speak("Here are the top news headlines:")
#         for i, article in enumerate(articles, 1):
#             headline = article.get('title', 'No title')
#             speak(f"Headline {i}: {headline}")
#             time.sleep(0.5)
#     except Exception:
#         speak("News service isn't responding right now. Please try later.")

# def get_weather(location):
#     coords = CITIES.get(location)
#     if not coords:
#         speak(f"I don't have weather data for {location}. Please try Mumbai, Delhi, Bangalore, or Chennai.")
#         return
#     lat, lon = coords
#     url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
#     try:
#         resp = requests.get(url)
#         data = resp.json()
#         weather = data.get('current_weather', {})
#         temperature = weather.get('temperature')
#         windspeed = weather.get('windspeed')
#         if temperature is None or windspeed is None:
#             speak("Couldn't fetch complete weather data.")
#             return
#         speak(f"The current temperature in {location.capitalize()} is {temperature}°C with wind speed {windspeed} kilometers per hour.")
#     except Exception:
#         speak("Failed to get weather information right now.")

# def get_stock(stock_symbol):
#     url = f"http://api.marketstack.com/v1/eod?access_key={MARKETSTACK_KEY}&symbols={stock_symbol.upper()}"
#     try:
#         response = requests.get(url)
#         data = response.json()
#         if 'data' not in data or not data['data']:
#             speak(f"Sorry, I couldn't find stock data for {stock_symbol}.")
#             return
#         latest = data['data'][0]
#         close_price = latest.get('close')
#         if close_price is not None:
#             speak(f"The latest closing price of {stock_symbol.upper()} is {close_price} dollars.")
#         else:
#             speak(f"Stock data for {stock_symbol} is currently unavailable.")
#     except Exception:
#         speak("Stock service is down at the moment.")

# def get_wikipedia_summary(topic):
#     try:
#         summary = wikipedia.summary(topic, sentences=2)
#         speak(summary)
#     except wikipedia.DisambiguationError as e:
#         speak(f"That topic is ambiguous. Did you mean {e.options[0]}?")
#     except Exception:
#         speak("Sorry, I couldn't find information on that topic.")

# def tell_joke():
#     jokes = [
#         "Why do Java developers wear glasses? Because they don't see sharp!",
#         "Why did the robot go on vacation? To recharge its batteries!",
#         "I would tell you a UDP joke, but you might not get it."
#     ]
#     speak(random.choice(jokes))


# # ---- INTENT PARSER ----
# def parse_command(cmd):
#     if "open" in cmd:
#         # Extract app name and launch
#         app_name = cmd.replace("open", "").strip()
#         if app_name:
#             launch_app(app_name)
#         else:
#             speak("Please tell me which app to open.")
#         return

#     if "reindex" in cmd:
#         # Delete old index and rebuild
#         if os.path.exists(APP_INDEX_FILE):
#             try:
#                 os.remove(APP_INDEX_FILE)
#             except Exception as e:
#                 speak("I couldn't delete the old app index. Please check permissions.")
#                 print(f"Error deleting app index file: {e}")
#                 return
#         speak("Reindexing applications now...")
#         load_or_build_app_index()
#         speak("App list updated!")
#         return

#     if "news" in cmd:
#         get_news()
#         return

#     if "weather" in cmd or "temperature" in cmd:
#         matched_city = None
#         for city in CITIES:
#             if city in cmd:
#                 matched_city = city
#                 break
#         if matched_city:
#             get_weather(matched_city)
#         else:
#             speak("Please specify the city for weather information.")
#         return

#     if "stock" in cmd or "market" in cmd or "price" in cmd:
#         # Attempt to extract stock symbol after keywords
#         parts = cmd.split()
#         stock_symbol = None
#         for idx, word in enumerate(parts):
#             if word in ['stock', 'price', 'market'] and idx + 1 < len(parts):
#                 stock_symbol = parts[idx + 1]
#                 break
#         if not stock_symbol:
#             stock_symbol = 'AAPL' # Default fallback
#         get_stock(stock_symbol)
#         return

#     if "who is" in cmd or "what is" in cmd:
#         topic = cmd.replace("who is", "").replace("what is", "").strip()
#         if topic:
#             get_wikipedia_summary(topic)
#         else:
#             speak("Please provide a topic to search on Wikipedia.")
#         return

#     if "joke" in cmd:
#         tell_joke()
#         return

#     if cmd in ['exit', 'quit', 'stop', 'bye']:
#         speak("Goodbye! Have a great day.")
#         sys.exit(0)

#     # If no known command matched
#     speak("Sorry, I didn't understand that. Try again or say 'help'.")

# # ---- MAIN LOOP ----

# def main():
#     speak("Hello! I am your AI assistant ready to serve. You can say things like 'open Chrome', 'tell me news', 'weather in Mumbai', 'stock price of Tesla', or 'tell me a joke'. Say 'exit' anytime to quit.")
#     while True:
#         cmd = get_voice_command()
#         if cmd:
#             parse_command(cmd)

# if __name__ == "__main__":
#     main()
# # This code is a simple AI assistant that can perform various tasks like fetching news, weather, stock prices, and more.
# ai_assistant_gui.py

#----------------------------------------------------------------------------------------------------------------------#

import sys
import os
import json
import random
import subprocess
import requests
import wikipedia
from difflib import get_close_matches
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPushButton, QVBoxLayout,
                             QWidget, QLabel)
from PyQt5.QtCore import QThread, pyqtSignal
import speech_recognition as sr
import pyttsx3

# For Windows shortcut resolving
import pythoncom
from win32com.shell import shell


APP_INDEX_FILE = "apps.json"


CITIES = {
    "mumbai": (19.076, 72.878),
    "delhi": (28.704, 77.103),
    "bangalore": (12.972, 77.595),
    "chennai": (13.082, 80.271),
}

# Marketstack API key
MARKETSTACK_KEY = "dab5f7ef7c04eea7b42adffb6d9e3790"
# NewsAPI key
NEWS_API_KEY = "5300c5c9353c47f2b9c86037dc4b721a"

engine = pyttsx3.init()

AI_WINDOW_INSTANCE = None
def speak(text):
    print("💬:", text)
    # Show assistant's answer in the chat if AIWindow instance exists
    global AI_WINDOW_INSTANCE
    if AI_WINDOW_INSTANCE is not None and hasattr(AI_WINDOW_INSTANCE, 'chat'):
        try:
            AI_WINDOW_INSTANCE.chat.append(f"<b>AI:</b> {text}")
        except Exception:
            pass
    else:
        # fallback: try to find a chat widget
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'chat'):
                        widget.chat.append(f"<b>AI:</b> {text}")
                        break
        except Exception:
            pass
    engine.say(text)
    engine.runAndWait()

def get_voice_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source, duration=1)
        print("Listening...")
        audio = recognizer.listen(source, phrase_time_limit=7)
    try:
        return recognizer.recognize_google(audio).lower()
    except Exception:
        speak("Didn't hear that. Try again.")
        return ""

def load_or_build_app_index():
    if not os.path.exists(APP_INDEX_FILE):
        search_dirs = [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs"),
            r"C:\Program Files", 
            r"C:\Program Files (x86)", 
            r"C:\Windows\System32"
        ]
        app_paths = {}
        for root_dir in search_dirs:
            if not root_dir or not os.path.exists(root_dir):
                continue
            for root, _, files in os.walk(root_dir):
                for file in files:
                    if file.lower().endswith(('.lnk', '.exe')):
                        name = os.path.splitext(file)[0].lower()
                        if name not in app_paths:
                            path = os.path.join(root, file)
                            app_paths[name] = path
        with open(APP_INDEX_FILE, "w") as f:
            json.dump(app_paths, f)
        print(f"Indexed {len(app_paths)} apps.")
        return app_paths
    else:
        with open(APP_INDEX_FILE, "r") as f:
            return json.load(f)

MANUAL_APPS = {
    "notepad": "notepad",
    "calculator": "calc",
    "paint": "mspaint",
    "file explorer": "explorer",
    "cmd": "cmd",
    "powershell": "powershell",
    # Update with your Windows username path for VSCode if needed:
    "vscode": r"C:\Users\YourUser\AppData\Local\Programs\Microsoft VS Code\Code.exe",
}

def launch_app(app_name):
    app_name = app_name.lower().strip()
    if app_name in MANUAL_APPS:
        try:
            subprocess.Popen(MANUAL_APPS[app_name])
            speak(f"Launching {app_name}!")
        except Exception as e:
            speak(f"Could not launch {app_name}. {e}")
        return

    apps = load_or_build_app_index()
    if app_name in apps:
        path = apps[app_name]
        # Resolve shortcut if needed
        if path.lower().endswith('.lnk'):
            try:
                shell_link = pythoncom.CoCreateInstance(
                    shell.CLSID_ShellLink, None,
                    pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
                persist_file = shell_link.QueryInterface(pythoncom.IID_IPersistFile)
                persist_file.Load(path)
                path, _ = shell_link.GetPath(shell.SLGP_RAWPATH)
            except Exception:
                pass
        try:
            subprocess.Popen(path)
            speak(f"Opening {app_name} for you!")
        except Exception as e:
            speak(f"Could not open {app_name}. {e}")
        return

    # Fuzzy matching fallback
    match = get_close_matches(app_name, apps.keys(), n=1, cutoff=0.6)
    if match:
        launch_app(match[0])
        return
    speak("Couldn't find that app. Try 'reindex' to refresh.")

def reindex_apps():
    if os.path.exists(APP_INDEX_FILE):
        os.remove(APP_INDEX_FILE)
    load_or_build_app_index()
    speak("Reindex complete! Latest installed apps synced.")

def get_news():
    try:
        url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"
        r = requests.get(url)
        articles = r.json().get("articles", [])[:3]
        if not articles:
            speak("No news found.")
            return
        speak("Here are the top news headlines:")
        for i, article in enumerate(articles, 1):
            headline = article.get('title', 'No title')
            speak(f"Headline {i}: {headline}")
    except Exception:
        speak("News fetch failed.")

def get_weather(city):
    coords = CITIES.get(city)
    if not coords:
        speak(f"No weather for {city}.")
        return
    lat, lon = coords
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    try:
        resp = requests.get(url)
        data = resp.json()
        weather = data.get('current_weather', {})
        temp, wind = weather.get('temperature'), weather.get('windspeed')
        if temp is not None and wind is not None:
            speak(f"In {city.title()}, it's {temp:.1f}°C, {wind} km/h wind.")
        else:
            speak("Weather incomplete.")
    except Exception:
        speak("Can't get weather.")

def get_stock(symbol):
    try:
        url = f"http://api.marketstack.com/v1/eod?access_key={MARKETSTACK_KEY}&symbols={symbol.upper()}"
        r = requests.get(url)
        data = r.json()
        # Marketstack returns 'data' as a list of dicts
        if 'data' in data and data['data']:
            latest = data['data'][0]
            close_price = latest.get('close')
            if close_price is not None:
                speak(f"The latest closing price of {symbol.upper()} is {close_price} dollars.")
            else:
                speak(f"Stock data for {symbol.upper()} is currently unavailable.")
        else:
            speak(f"No data for {symbol.upper()}.")
    except Exception:
        speak("Stock API not reachable.")

def get_wiki(query):
    try:
        summary = wikipedia.summary(query, sentences=2)
        speak(summary)
    except Exception:
        speak("No Wikipedia summary found.")

def tell_joke():
    jokes = [
        "Why don't robots get afraid? Because they have nerves of steel.",
        "Why was the computer cold? It left its Windows open.",
        "My CPU has a crush on your GPU.",
    ]
    speak(random.choice(jokes))

def handle_command(cmd):
    c = cmd.lower()
    if "open" in c:
        app = c.replace("open", "").strip()
        if app:
            launch_app(app)
        else:
            speak("Tell me which app to open.")
        return
    if "reindex" in c:
        reindex_apps()
        return
    if "news" in c:
        def on_done(type_, msg):
            speak(msg)
        thread = WorkerThread(get_news)
        thread.result.connect(on_done)
        if hasattr(AI_WINDOW_INSTANCE, '_threads'):
            AI_WINDOW_INSTANCE._threads.append(thread)
        thread.finished.connect(lambda: AI_WINDOW_INSTANCE._threads.remove(thread) if thread in AI_WINDOW_INSTANCE._threads else None)
        thread.start()
        return
    if "weather" in c:
        for city in CITIES:
            if city in c:
                def on_done(type_, msg):
                    speak(msg)
                thread = WorkerThread(get_weather, city)
                thread.result.connect(on_done)
                if hasattr(AI_WINDOW_INSTANCE, '_threads'):
                    AI_WINDOW_INSTANCE._threads.append(thread)
                thread.finished.connect(lambda: AI_WINDOW_INSTANCE._threads.remove(thread) if thread in AI_WINDOW_INSTANCE._threads else None)
                thread.start()
                return
        speak("Say the city for weather: Mumbai, Delhi, Bangalore, Chennai.")
        return
    if any(w in c for w in ["stock", "market", "price"]):
        import re
        match = re.search(r'(?:stock|price|market)(?:\s+price)?(?:\s+of)?\s+([a-zA-Z0-9_.-]+)', c)
        symbol = None
        if match:
            symbol = match.group(1).upper()
        else:
            parts = c.split()
            for i, word in enumerate(parts):
                if word in ["stock", "price", "market"] and i + 1 < len(parts):
                    symbol = parts[i + 1].upper()
                    break
        if not symbol:
            symbol = "AAPL"
        def on_done(type_, msg):
            speak(msg)
        thread = WorkerThread(get_stock, symbol)
        thread.result.connect(on_done)
        if hasattr(AI_WINDOW_INSTANCE, '_threads'):
            AI_WINDOW_INSTANCE._threads.append(thread)
        thread.finished.connect(lambda: AI_WINDOW_INSTANCE._threads.remove(thread) if thread in AI_WINDOW_INSTANCE._threads else None)
        thread.start()
        return
    if "who is" in c or "what is" in c:
        topic = c.replace("who is", "").replace("what is", "").strip()
        if topic:
            def on_done(type_, msg):
                speak(msg)
            thread = WorkerThread(get_wiki, topic)
            thread.result.connect(on_done)
            if hasattr(AI_WINDOW_INSTANCE, '_threads'):
                AI_WINDOW_INSTANCE._threads.append(thread)
            thread.finished.connect(lambda: AI_WINDOW_INSTANCE._threads.remove(thread) if thread in AI_WINDOW_INSTANCE._threads else None)
            thread.start()
        else:
            speak("Tell me a topic to search for.")
        return
    if "joke" in c:
        tell_joke()
        return
    if c in ["exit", "quit", "bye", "stop"]:
        speak("Goodbye! Stay awesome.")
        sys.exit(0)
    speak("Sorry, didn't get that. Try again or rephrase.")

# --- WorkerThread for running tasks in background ---
class WorkerThread(QThread):
    result = pyqtSignal(str, str)  # (type, message)
    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            msg = self.func(*self.args, **self.kwargs)
            if msg:
                self.result.emit("success", msg)
        except Exception as e:
            self.result.emit("error", str(e))


# --- Main AIWindow class for the assistant GUI ---
class AIWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔥 The DRAX AI")
        self.setFixedSize(570, 680)
        self.setStyleSheet("background: #000; color:#FFD600; font-family: Arial, Helvetica, sans-serif; border-radius: 16px;")
        banner = QLabel("🐲 Speak or type! Try news, weather, open notepad, joke, reindex, exit.")
        banner.setStyleSheet("font-size:19px; padding:12px; color:#FFD600; background: #000; font-family: Arial, Helvetica, sans-serif;")
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet("background:#000; color:#FFD600; border-radius:9px; font-size:16px; font-family: Arial, Helvetica, sans-serif;")
        from PyQt5.QtWidgets import QLineEdit, QHBoxLayout
        type_layout = QHBoxLayout()
        self.type_input = QLineEdit()
        self.type_input.setPlaceholderText("Type your command here...")
        self.type_input.setStyleSheet("background:#000; color:#FFD600; font-size:16px; border-radius:7px; padding:8px; font-family: Arial, Helvetica, sans-serif; border: 1px solid #FFD600;")
        self.type_input.returnPressed.connect(self.handle_type_command)
        type_btn = QPushButton("Send")
        type_btn.setStyleSheet("background:#000; color:#FFD600; font-size:16px; padding:8px 18px; border-radius:7px; font-family: Arial, Helvetica, sans-serif; border: 1.5px solid #FFD600;")
        type_btn.clicked.connect(self.handle_type_command)
        type_layout.addWidget(self.type_input)
        type_layout.addWidget(type_btn)
        layout = QVBoxLayout()
        layout.addWidget(banner)
        layout.addWidget(self.chat)
        layout.addLayout(type_layout)
        box = QWidget()
        box.setLayout(layout)
        self.setCentralWidget(box)
        self._threads = []  # To keep references to threads

    def handle_type_command(self):
        text = self.type_input.text().strip()
        if text:
            self.chat.append(f"<b>You:</b> {text}")
            handle_command(text)
            self.type_input.clear()


# --- Main block to launch the app ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    global AI_WINDOW_INSTANCE
    AI_WINDOW_INSTANCE = AIWindow()
    AI_WINDOW_INSTANCE.show()
    sys.exit(app.exec_())