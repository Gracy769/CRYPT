import os
import threading
import time
import random
import requests
from flask import Flask
from mnemonic import Mnemonic
from eth_account import Account

# REQUIRED: Enable HD wallet features for mnemonic derivation
Account.enable_unaudited_hdwallet_features()

app = Flask(__name__)

# CONFIGURATION
# Using a robust list. If one fails, the scraper moves to the next.
RPC_URLS = [
    "https://eth.llamarpc.com",
    "https://cloudflare-eth.com",
    "https://rpc.ankr.com/eth",
    "https://eth-mainnet.public.blastapi.io"
]

# Shared state for the web monitor
stats = {
    "checked": 0,
    "hits": 0,
    "last_address": "None",
    "status": "Initializing"
}

def scraper_worker():
    """The heavy lifter running in the background."""
    mnemo = Mnemonic("english")
    stats["status"] = "Running"
    
    # Pre-configure session for performance and to mimic a real browser
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Content-Type': 'application/json'
    })

    while True:
        try:
            # 1. Generate Mnemonic
            entropy = os.urandom(16)
            phrase = mnemo.to_mnemonic(entropy)
            
            # 2. Derive Address
            # This is CPU intensive, stays in the background thread
            acc = Account.from_mnemonic(phrase)
            address = acc.address
            
            # 3. Check Balance with Rotation & Error Handling
            rpc_url = random.choice(RPC_URLS)
            payload = {
                "jsonrpc": "2.0", 
                "method": "eth_getBalance", 
                "params": [address, "latest"], 
                "id": 1
            }
            
            response = session.post(rpc_url, json=payload, timeout=5)
            
            if response.status_code == 200:
                result = response.json().get('result', '0x0')
                balance_wei = int(result, 16)
                
                if balance_wei > 0:
                    stats["hits"] += 1
                    # LOG HITS IMMEDIATELY TO DISK/CONSOLE
                    with open("hits.log", "a") as f:
                        f.write(f"Mnemonic: {phrase}\nAddr: {address}\nBal: {balance_wei/10**18} ETH\n---\n")
                
                stats["checked"] += 1
                stats["last_address"] = address
            
            elif response.status_code == 429:
                # Throttled - cool down
                time.sleep(10)
                
        except Exception as e:
            # Don't let a network hiccup kill the whole script
            time.sleep(1)
            continue

@app.route('/')
def dashboard():
    """Simple web interface to check status from your phone/PC."""
    return {
        "status": stats["status"],
        "total_checked": stats["checked"],
        "hits_found": stats["hits"],
        "latest_scan": stats["last_address"],
        "uptime_note": "Ensure you use an uptime pinger to keep the cloud instance awake."
    }

if __name__ == "__main__":
    # Launch scraper in background
    threading.Thread(target=scraper_worker, daemon=True).start()
    
    # Cloud providers like Render/Heroku/Railway pass the PORT env variable
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
