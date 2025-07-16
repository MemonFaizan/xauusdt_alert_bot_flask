from flask import Flask
import threading
import bot

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Gold Sniper Bot Running!"

def run_bot():
    bot.main()

if __name__ == "__main__":
    threading.Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
