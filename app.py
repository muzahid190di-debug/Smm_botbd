import os
import json
import requests
from flask import Flask, request, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

# ==================== কনফিগারেশন ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
SMM_API_KEY = os.environ.get("SMM_API_KEY", "YOUR_BD_SMM_PANEL_API_KEY")
SMM_API_URL = "https://bdsmmpanel.com/api/v2"

# ইউজার ডাটা এবং ওয়ালেট ব্যালেন্স জমানোর সিম্পল ফাইল ডাটাবেস
DB_FILE = "users_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# সার্ভিস লিস্ট ও প্রফিট প্রাইস (টাকা)
SERVICES_CONFIG = {
    "1": {"id": 101, "name": "🔥 Facebook Followers (Non-Drop)", "price_per_1k": 120},
    "2": {"id": 202, "name": "⚡ YouTube Subscribers (Real)", "price_per_1k": 350},
    "3": {"id": 303, "name": "🚀 TikTok Followers (Instant)", "price_per_1k": 150}
}

app = Flask(__name__)

# ==================== আকর্ষণীয় ফ্রন্টএন্ড মিনি অ্যাপ (UI) ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD SMM Panel Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 15px; margin: 0; }
        .container { max-width: 400px; margin: auto; }
        .card { background: #1e293b; padding: 20px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); margin-bottom: 15px; border: 1px solid #334155; }
        .wallet-card { background: linear-gradient(135deg, #3b82f6, #1d4ed8); color: white; padding: 15px; border-radius: 14px; text-align: center; margin-bottom: 15px; }
        h2 { text-align: center; color: #38bdf8; margin-top: 0; font-size: 22px; }
        label { font-weight: 600; margin-top: 12px; display: block; font-size: 14px; color: #cbd5e1; }
        select, input { width: 100%; padding: 12px; margin-top: 6px; border-radius: 10px; border: 1px solid #475569; background: #0f172a; color: white; box-sizing: border-box; font-size: 14px; }
        .price-box { margin-top: 15px; background: #334155; padding: 12px; border-radius: 10px; font-weight: bold; color: #38bdf8; text-align: center; }
        button { width: 100%; background: #2563eb; color: white; border: none; padding: 14px; border-radius: 10px; font-size: 16px; font-weight: bold; margin-top: 15px; cursor: pointer; transition: 0.3s; }
        button:hover { background: #1d4ed8; }
        .tab-buttons { display: flex; gap: 10px; margin-bottom: 15px; }
        .tab-btn { flex: 1; padding: 10px; background: #334155; border: none; color: white; border-radius: 8px; cursor: pointer; font-weight: bold; }
        .tab-btn.active { background: #2563eb; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="wallet-card">
            <h3 style="margin:0; font-size: 14px; opacity: 0.9;">তোর বর্তমান ব্যালেন্স</h3>
            <h1 style="margin: 5px 0 0 0; font-size: 28px;">৳ <span id="userBalance">0.00</span></h1>
        </div>

        <div class="tab-buttons">
            <button class="tab-btn active" onclick="switchTab('order')">🚀 সার্ভিস অর্ডার</button>
            <button class="tab-btn" onclick="switchTab('deposit')">➕ ব্যালেন্স অ্যাড</button>
        </div>

        <!-- অর্ডার সেকশন -->
        <div id="orderSection" class="card">
            <h2>নতুন অর্ডার করুন</h2>
            <label for="service">সার্ভিস নির্বাচন করো:</label>
            <select id="service" onchange="calculatePrice()">
                {% for key, s in services.items() %}
                    <option value="{{ key }}" data-price="{{ s.price_per_1k }}">{{ s.name }} (৳{{ s.price_per_1k }}/1k)</option>
                {% endfor %}
            </select>

            <label for="link">টার্গেট লিংক (Profile/Video URL):</label>
            <input type="text" id="link" placeholder="https://..." required>

            <label for="quantity">পরিমাণ (Quantity):</label>
            <input type="number" id="quantity" value="1000" min="100" oninput="calculatePrice()">

            <div class="price-box" id="totalPrice">মোট খরচ: ৳0</div>
            <button onclick="submitOrder()">অর্ডার কনফার্ম করুন</button>
        </div>

        <!-- ডিপোজিট সেকশন -->
        <div id="depositSection" class="card hidden">
            <h2>বিকাশ এ ট্যাকা অ্যাড (মিন: ১০৳)</h2>
            <p style="font-size: 13px; color: #94a3b8; text-align: center;">আমাদের বিকাশ পার্সোনাল নাম্বারে Send Money করে নিচে ট্রানজেকশন আইডি দাও।</p>
            <div style="background: #0f172a; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; color: #fbbf24; margin-bottom: 10px;">
                বিকাশ পার্সোনাল: 01700000000
            </div>
            
            <label for="depAmount">পরিমাণ (টাকা):</label>
            <input type="number" id="depAmount" placeholder="১০" min="10" required>

            <label for="trxId">বিকাশ ট্রানজেকশন আইডি (TrxID):</label>
            <input type="text" id="trxId" placeholder="9N7X..." required>

            <button onclick="submitDeposit()">পেমেন্ট সাবমিট করো</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        
        let userTgId = tg.initDataUnsafe?.user?.id || "12345";

        // ডেমো ব্যালেন্স সিঙ্ক (ব্যাকএন্ড থেকে রিয়েল ডাটা আসবে)
        document.getElementById('userBalance').innerText = "500.00"; 

        function switchTab(tab) {
            if(tab === 'order') {
                document.getElementById('orderSection').classList.remove('hidden');
                document.getElementById('depositSection').classList.add('hidden');
                document.querySelectorAll('.tab-btn')[0].classList.add('active');
                document.querySelectorAll('.tab-btn')[1].classList.remove('active');
            } else {
                document.getElementById('orderSection').classList.add('hidden');
                document.getElementById('depositSection').classList.remove('hidden');
                document.querySelectorAll('.tab-btn')[1].classList.add('active');
                document.querySelectorAll('.tab-btn')[0].classList.remove('active');
            }
        }

        function calculatePrice() {
            const select = document.getElementById('service');
            const pricePer1k = select.options[select.selectedIndex].getAttribute('data-price');
            const qty = document.getElementById('quantity').value || 0;
            const total = (qty / 1000) * pricePer1k;
            document.getElementById('totalPrice').innerText = "মোট খরচ: ৳" + total.toFixed(2);
        }

        function submitOrder() {
            const serviceKey = document.getElementById('service').value;
            const link = document.getElementById('link').value;
            const quantity = document.getElementById('quantity').value;

            if(!link || !quantity || quantity <= 0) {
                alert("দয়া করে সঠিক লিংক ও পরিমাণ দাও!");
                return;
            }

            tg.sendData(JSON.stringify({
                type: "order",
                user_id: userTgId,
                service_key: serviceKey,
                link: link,
                quantity: quantity
            }));
            tg.close();
        }

        function submitDeposit() {
            const amount = document.getElementById('depAmount').value;
            const trxId = document.getElementById('trxId').value;

            if(!amount || amount < 10 || !trxId) {
                alert("ন্যূনতম ১০ টাকা এবং সঠিক TrxID দাও!");
                return;
            }

            tg.sendData(JSON.stringify({
                type: "deposit",
                user_id: userTgId,
                amount: amount,
                trx_id: trxId
            }));
            tg.close();
        }

        calculatePrice();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, services=SERVICES_CONFIG)

# ==================== টেলিগ্রাম বট ও ব্যাকএন্ড লজিক ====================
telegram_app = None # পরে ইনিশিয়ালাইজ হবে

# ফ্লাস্কের মাধ্যমে বটের রাউট হ্যান্ডেল করার প্রস্তুতি
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = Update.de_json(json.loads(json_str), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return 'OK', 200
