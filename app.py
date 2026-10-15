import json
import os
import requests
from flask import Flask, render_template_string, request

# ==================== কনফিগারেশন ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
SMM_API_KEY = os.environ.get("SMM_API_KEY", "YOUR_BD_SMM_PANEL_API_KEY")
SMM_API_URL = "https://bdsmmpanel.com/api/v2"

DB_FILE = "users_db.json"
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "YOUR_ADMIN_TELEGRAM_ID")


def load_db():
  if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
      return json.load(f)
  return {}


def save_db(data):
  with open(DB_FILE, "w") as f:
    json.dump(data, f, indent=4)


# SMM প্যানেল থেকে সমস্ত লাইভ সার্ভিস ফেচ ও ডায়নামিক প্রফিট মার্জিন যোগ করার লজিক
def get_smm_services():
  try:
    payload = {"key": SMM_API_KEY, "action": "services"}
    response = requests.post(SMM_API_URL, data=payload)
    if response.status_code == 200:
      services = response.json()
      formatted_services = {}
      for s in services:
        original_rate = float(s.get("rate", 0))

        # 🎯 তোর চাহিদামতো অটোমেটিক প্রফিট যোগ করার স্মার্ট লজিক:
        if original_rate <= 50:
          profit = 10  # ছোট অফারে ১০ টাকা লাভ
        elif original_rate <= 150:
          profit = 20  # মাঝারি অফারে ২০ টাকা লাভ
        elif original_rate <= 300:
          profit = 35  # বড় অফারে ৩৫ টাকা লাভ
        else:
          profit = 50  # প্রিমিয়াম/অনেক দামি অফারে ৫০ টাকা লাভ

        final_rate = round(original_rate + profit, 2)

        formatted_services[str(s["service"])] = {
            "name": s["name"],
            "category": s.get("category", "General"),
            "price_per_1k": final_rate,
            "min": s.get("min", 10),
            "max": s.get("max", 10000),
        }
      return formatted_services
  except Exception:
    pass
  return {}


app = Flask(__name__)

# ==================== প্রিমিয়াম ও আধুনিক মিনি অ্যাপ UI ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BD SMM Panel Mini App</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {
            --bg-color: #0b0f19;
            --card-bg: rgba(30, 41, 59, 0.7);
            --accent: #38bdf8;
            --accent-gradient: linear-gradient(135deg, #3b82f6, #06b6d4);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
        }
        body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--bg-color); color: var(--text-main); padding: 12px; margin: 0; }
        .container { max-width: 450px; margin: auto; }
        
        .wallet-card { 
            background: var(--accent-gradient); 
            color: white; padding: 20px; border-radius: 20px; text-align: center; margin-bottom: 15px; 
            box-shadow: 0 10px 25px rgba(59, 130, 246, 0.3); 
        }
        .wallet-card h3 { margin: 0; font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px; }
        .wallet-card h1 { margin: 8px 0 0 0; font-size: 32px; font-weight: 800; }

        .tab-buttons { display: flex; gap: 8px; margin-bottom: 15px; background: rgba(15, 23, 42, 0.8); padding: 5px; border-radius: 14px; border: 1px solid var(--border); }
        .tab-btn { flex: 1; padding: 12px; background: transparent; border: none; color: var(--text-muted); border-radius: 10px; cursor: pointer; font-weight: 700; font-size: 14px; transition: 0.3s; }
        .tab-btn.active { background: var(--accent-gradient); color: white; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4); }

        .card { background: var(--card-bg); backdrop-filter: blur(10px); padding: 20px; border-radius: 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); margin-bottom: 15px; border: 1px solid var(--border); }
        h2 { text-align: center; color: var(--accent); margin-top: 0; font-size: 18px; font-weight: 700; margin-bottom: 15px; }
        
        label { font-weight: 600; margin-top: 12px; display: block; font-size: 13px; color: var(--text-muted); }
        select, input { width: 100%; padding: 14px; margin-top: 6px; border-radius: 12px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.9); color: white; box-sizing: border-box; font-size: 14px; outline: none; transition: 0.3s; }
        select:focus, input:focus { border-color: var(--accent); box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2); }
        
        .price-box { margin-top: 15px; background: rgba(15, 23, 42, 0.8); padding: 14px; border-radius: 12px; font-weight: 700; color: var(--accent); text-align: center; border: 1px solid var(--border); font-size: 16px; }
        
        button.action-btn { width: 100%; background: var(--accent-gradient); color: white; border: none; padding: 16px; border-radius: 12px; font-size: 16px; font-weight: 700; margin-top: 18px; cursor: pointer; box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4); transition: 0.3s; }
        button.action-btn:active { transform: scale(0.98); }

        .bkash-box { background: rgba(244, 63, 94, 0.1); border: 1px dashed #f43f5e; padding: 15px; border-radius: 14px; text-align: center; margin-bottom: 15px; }
        .bkash-number { font-size: 18px; font-weight: 800; color: #fb7185; margin-top: 5px; letter-spacing: 1px; }

        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="wallet-card">
            <h3>আপনার বর্তমান ব্যালেন্স</h3>
            <h1>৳ <span id="userBalance">0.00</span></h1>
        </div>

        <div class="tab-buttons">
            <button class="tab-btn active" onclick="switchTab('order')">🚀 সার্ভিস অর্ডার</button>
            <button class="tab-btn" onclick="switchTab('deposit')">➕ ব্যালেন্স অ্যাড</button>
        </div>

        <!-- অর্ডার সেকশন -->
        <div id="orderSection" class="card">
            <h2>সরাসরি এসএসএম সার্ভিস অর্ডার</h2>
            
            <label for="service">সার্ভিস নির্বাচন করুন:</label>
            <select id="service" onchange="calculatePrice()">
                {% for key, s in services.items() %}
                    <option value="{{ key }}" data-price="{{ s.price_per_1k }}">{{ s.name }} (৳{{ s.price_per_1k }}/1k)</option>
                {% endfor %}
            </select>

            <label for="link">টার্গেট লিংক (Profile/Video URL):</label>
            <input type="text" id="link" placeholder="https://..." required>

            <label for="quantity">পরিমাণ (Quantity):</label>
            <input type="number" id="quantity" value="1000" min="10" oninput="calculatePrice()">

            <div class="price-box" id="totalPrice">মোট খরচ: ৳0</div>
            <button class="action-btn" onclick="submitOrder()">অর্ডার কনফার্ম করুন</button>
        </div>

        <!-- ডিপোজিট সেকশন -->
        <div id="depositSection" class="card hidden">
            <h2>বিকাশ ব্যালেন্স যোগ করুন</h2>
            <div class="bkash-box">
                <span style="font-size: 13px; color: #cbd5e1;">আমাদের বিকাশ পার্সোনাল নাম্বারে Send Money করুন:</span>
                <div class="bkash-number">01605969856</div>
            </div>
            
            <label for="depAmount">টাকার পরিমাণ:</label>
            <input type="number" id="depAmount" placeholder="যেমন: ১০০" min="10" required>

            <label for="trxId">বিকাশ ট্রানজেকশন আইডি (TrxID):</label>
            <input type="text" id="trxId" placeholder="যেমন: 9N7X..." required>

            <button class="action-btn" onclick="submitDeposit()">পেমেন্ট সাবমিট করুন</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        let userTgId = tg.initDataUnsafe?.user?.id || "12345";
        let username = tg.initDataUnsafe?.user?.username || "Unknown";
        let firstName = tg.initDataUnsafe?.user?.first_name || "User";

        fetch('/get_balance?user_id=' + userTgId)
            .then(res => res.json())
            .then(data => {
                document.getElementById('userBalance').innerText = data.balance.toFixed(2);
            });

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
                alert("দয়া করে সঠিক লিংক ও পরিমাণ দিন!");
                return;
            }

            fetch('/api/order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userTgId, service_key: serviceKey, link: link, quantity: quantity})
            }).then(res => res.json()).then(data => {
                alert(data.message);
                if(data.success) location.reload();
            });
        }

        function submitDeposit() {
            const amount = document.getElementById('depAmount').value;
            const trxId = document.getElementById('trxId').value;

            if(!amount || amount < 10 || !trxId) {
                alert("ন্যূনতম ১০ টাকা এবং সঠিক TrxID দিন!");
                return;
            }

            fetch('/api/deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userTgId, username: username, first_name: firstName, amount: amount, trx_id: trxId})
            }).then(res => res.json()).then(data => {
                alert(data.message);
                tg.close();
            });
        }

        calculatePrice();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
  services = get_smm_services()
  return render_template_string(HTML_TEMPLATE, services=services)


@app.route("/get_balance")
def get_balance():
  user_id = request.args.get("user_id")
  db = load_db()
  user_data = db.get(str(user_id), {"balance": 0.0})
  return {"balance": user_data.get("balance", 0.0)}


@app.route("/api/order", methods=["POST"])
def api_order():
  data = request.json
  user_id = str(data.get("user_id"))
  service_key = data.get("service_key")
  link = data.get("link")
  quantity = int(data.get("quantity"))

  services = get_smm_services()
  if service_key not in services:
    return {"success": False, "message": "সার্ভিসটি পাওয়া যায়নি!"}

  service_info = services[service_key]
  total_cost = (quantity / 1000) * service_info["price_per_1k"]

  db = load_db()
  if user_id not in db:
    db[user_id] = {"balance": 0.0}

  if db[user_id]["balance"] < total_cost:
    return {
        "success": False,
        "message": (
            "পর্যাপ্ত ব্যালেন্স নেই! প্রথমে বিকাশে পেমেন্ট করে ব্যালেন্স যোগ করুন।"
        ),
    }

  # SMM প্যানেলে অটোমেটিক অর্ডার প্লেস
  payload = {
      "key": SMM_API_KEY,
      "action": "add",
      "service": service_key,
      "link": link,
      "quantity": quantity,
  }
  resp = requests.post(SMM_API_URL, data=payload).json()

  if "order" in resp:
    db[user_id]["balance"] -= total_cost
    save_db(db)
    return {
        "success": True,
        "message": f"অর্ডার সফল হয়েছে! অর্ডার আইডি: {resp['order']}",
    }
  else:
    return {
        "success": False,
        "message": f"অর্ডার ফেইল করেছে: {resp.get('error', 'টেকনিক্যাল সমস্যা')}",
    }


@app.route("/api/deposit", methods=["POST"])
def api_deposit():
  data = request.json
  user_id = str(data.get("user_id"))
  username = data.get("username", "Unknown")
  first_name = data.get("first_name", "User")
  amount = float(data.get("amount"))
  trx_id = data.get("trx_id")

  if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "YOUR_ADMIN_TELEGRAM_ID":
    msg = (
        f"🔔 **নতুন ডিপোজিট রিকোয়েস্ট!**\n\n👤 নাম: {first_name} (@{username})\n🆔"
        f" আইডি: `{user_id}`\n💰 পরিমাণ: ৳{amount}\n💳 TrxID:"
        f" `{trx_id}`\n\nএপ্রুভ করতে নিচের বাটনে ক্লিক করুন:"
    )
    keyboard = {
        "inline_keyboard": [[{
            "text": f"✅ এপ্রুভ করুন (৳{amount})",
            "callback_data": f"app_{user_id}_{amount}",
        }]]
    }
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": ADMIN_CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        },
    )

  return {
      "success": True,
      "message": (
          "পেমেন্ট রিকোয়েস্ট সাবমিট হয়েছে! অ্যাডমিন যাচাই করে দ্রুত ব্যালেন্স"
          " যোগ করে দেবেন।"
      ),
  }


# ==================== টেলিগ্রাম বট ওয়েবহুক ====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
  data = request.get_json()
  if not data:
    return "OK", 200

  if "message" in data:
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    if text.startswith("/start"):
      web_app_url = "https://smm-botbd.onrender.com"
      payload = {
          "chat_id": chat_id,
          "text": (
              "আসসালামু আলাইকুম!\n\nআমাদের অফিশিয়াল SMM প্যানেলে আপনাকে স্বাগতম।"
              " সেবা নিতে নিচের বাটনে ক্লিক করে মিনি অ্যাপ খুলুন:"
          ),
          "reply_markup": {
              "inline_keyboard": [[{
                  "text": "🚀 এসএসএম প্যানেল মিনি অ্যাপ খুলুন",
                  "web_app": {"url": web_app_url},
              }]]
          },
      }
      requests.post(
          f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload
      )

  elif "callback_query" in data:
    cq = data["callback_query"]
    cq_id = cq["id"]
    data_val = cq.get("data", "")
    admin_chat_id = cq["message"]["chat"]["id"]

    if data_val.startswith("app_"):
      parts = data_val.split("_")
      target_user = parts[1]
      add_amount = float(parts[2])

      db = load_db()
      if target_user not in db:
        db[target_user] = {"balance": 0.0}
      db[target_user]["balance"] += add_amount
      save_db(db)

      requests.post(
          f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
          json={
              "chat_id": target_user,
              "text": (
                  f"আলহামদুলিল্লাহ! আপনার একাউন্টে ৳{add_amount} সফলভাবে যোগ করা"
                  " হয়েছে।"
              ),
          },
      )

      requests.post(
          f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
          json={
              "chat_id": admin_chat_id,
              "text": (
                  f"✅ সফলভাবে ইউজার {target_user}-কে ৳{add_amount} ব্যালেন্স"
                  " এপ্রুভ করা হয়েছে!"
              ),
          },
      )

      requests.post(
          f"https://api.telegram.org/bot{BOT_TOKEN}/answercallbackquery",
          json={"callback_query_id": cq_id, "text": "এপ্রুভড হয়েছে!"},
      )

  return "OK", 200


def set_webhook_automatically():
  if BOT_TOKEN and BOT_TOKEN != "YOUR_TELEGRAM_BOT_TOKEN":
    webhook_url = f"https://smm-botbd.onrender.com/{BOT_TOKEN}"
    try:
      requests.get(
          f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}"
      )
    except Exception:
      pass


if __name__ == "__main__":
  set_webhook_automatically()
  port = int(os.environ.get("PORT", 5000))
  app.run(host="0.0.0.0", port=port)
