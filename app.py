from flask import Flask
import threading
import bot  # your main signal script file

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Gold Sniper Bot Running!"

# Directly start thread without using decorator
def run_bot():
    bot.main()

# Start thread before app.run()
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=10000)
