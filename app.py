from flask import Flask
import threading
import bot  # your original logic from bot.py

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Gold Sniper Alert Bot Running on Render with Flask"

def run_bot():
    bot.main()

@app.before_first_request
def activate_bot():
    thread = threading.Thread(target=run_bot)
    thread.start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
