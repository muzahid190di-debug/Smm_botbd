import json
import os
import requests
from flask import Flask, render_template_string, request

# ==================== কনফিগারেশন ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
SMM_API_KEY = os.environ.get("SMM_API_KEY", "YOUR_BD_SMM_PANEL_API_KEY")
SMM_API_URL = "https://bdsmmpanel.com/api/v2"

# ডাটাবেস ফাইল
DB_FILE = "users_db.json"
ADMIN_CHAT_ID = os.environ.get(
    "ADMIN_CHAT_ID", "YOUR_ADMIN_TELEGRAM_ID"
)  # তোর টেলিগ্রাম আইডি এখানে দিবি


def load_db():
  if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
      return json.load(f)
  return {}


def save_db(data):
  with open(DB_FILE, "w") as f:
    json.dump(data, f, indent=4)


# SMM API থেকে রিয়েল সার্ভিস ফেচ করার ফাংশন
def get_smm_services():
  try:
    payload = {"key": SMM_API_KEY, "action": "services"}
    response = requests.post(SMM_API_URL, data=payload)
    if response.status_code == 200:
      services = response.json()
      # প্রথম ২০টি সার্ভিস ফিল্টার করে সুন্দর ফরম্যাটে নেওয়া
      formatted_services = {}
      for s in services[:20]:
        # পাইকারি দামের সাথে প্রফিট যোগ করে রিটেইল প্রাইস নির্ধারণ (যেমন ২০% প্রফিট)
        rate = float(s.get("rate", 100))
        sell_rate = round(rate * 1.3, 2)
        formatted_services[str(s["service"])] = {
            "name": s["name"],
            "price_per_1k": sell_rate,
            "min": s.get("min", 10),
            "max": s.get("max", 10000),
        }
      return formatted_services
  except Exception:
    pass

  # API ফেইল করলে ডিফল্ট কিছু সার্ভিস ব্যাকআপ
  return {
      "101": {
          "name": "🔥 Facebook Followers (Non-Drop)",
          "price_per_1k": 150,
          "min": 100,
          "max": 50000,
      },
      "202": {
          "name": "⚡ YouTube Subscribers (Real)",
          "price_per_1k": 400,
          "min": 50,
          "max": 10000,
      },
  }


app = Flask(__name__)

# ==================== প্রিমিয়াম মিনি অ্যাপ ফ্রন্টএন্ড (UI) ====================
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
        h2 { text-align: center; color: #38bdf8; margin-top: 0; font-size: 20px; }
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
            <input type="number" id="quantity" value="1000" min="10" oninput="calculatePrice()">

            <div class="price-box" id="totalPrice">মোট খরচ: ৳0</div>
            <button onclick="submitOrder()">অর্ডার কনফার্ম করুন</button>
        </div>

        <!-- ডিপোজিট সেকশন -->
        <div id="depositSection" class="card hidden">
            <h2>বিকাশে টাকা অ্যাড (মিন: ১০৳)</h2>
            <p style="font-size: 13px; color: #94a3b8; text-align: center;">আমাদের বিকাশ পার্সোনাল নাম্বারে Send Money করে নিচে ট্রানজেকশন আইডি দাও।</p>
            <div style="background: #0f172a; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; color: #fbbf24; margin-bottom: 10px;">
                বিকাশ পার্সোনাল: 01605969856
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
        let username = tg.initDataUnsafe?.user?.username || "Unknown";

        // ব্যালেন্স লোড করার ফেচ
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
                alert("দয়া করে সঠিক লিংক ও পরিমাণ দাও!");
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
                alert("ন্যূনতম ১০ টাকা এবং সঠিক TrxID দাও!");
                return;
            }

            fetch('/api/deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userTgId, username: username, amount: amount, trx_id: trxId})
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
        "message": "তোর পর্যাপ্ত ব্যালেন্স নেই! আগে ব্যালেন্স অ্যাড কর।",
    }

  # SMM প্যানেলে অর্ডার প্লেস করা
  payload = {
      "key": SMM_API_KEY,
      "action": "add",
      "service": service_info["id"],
      "link": link,
      "quantity": quantity,
  }
  resp = requests.post(SMM_API_URL, data=payload).json()

  if "order" in resp:
    db[user_id]["balance"] -= total_cost
    save_db(db)
    return {
        "success": True,
        "message": f"আলহামদুলিল্লাহ! অর্ডার সফল হয়েছে। অর্ডার আইডি: {resp['order']}",
    }
  else:
    return {
        "success": False,
        "message": f"অর্ডার ফেইল করেছে: {resp.get('error', 'অজানা সমস্যা')}",
    }


@app.route("/api/deposit", methods=["POST"])
def api_deposit():
  data = request.json
  user_id = str(data.get("user_id"))
  username = data.get("username", "Unknown")
  amount = float(data.get("amount"))
  trx_id = data.get("trx_id")

  # অ্যাডমিনকে টেলিগ্রামে নোটিফিকেশন পাঠানো যাতে সে এপ্রুভ করতে পারে
  if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "YOUR_ADMIN_TELEGRAM_ID":
    msg = (
        f"🔔 **নতুন ডিপোজিট রিকোয়েস্ট!**\n\n👤 ইউজার আইডি: `{user_id}`\n🌐 ইউজারনেম:"
        f" @{username}\n💰 পরিমাণ: ৳{amount}\n💳 TrxID:"
        f" `{trx_id}`\n\nএপ্রুভ করতে নিচের কমান্ড দাও:\n`/addbal {user_id}"
        f" {amount}`"
    )
    requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
    )

  return {
      "success": True,
      "message": (
          "পেমেন্ট রিকোয়েস্ট সফলভাবে সাবমিট হয়েছে! অ্যাডমিন যাচাই করে ব্যালেন্স"
          " যোগ করে দেবে।"
      ),
  }


# ==================== টেলিগ্রাম বট ওয়েবহুক ও কমান্ড ====================
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
  data = request.get_json()
  if data and "message" in data:
    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")
    user_id = str(data["message"]["from"]["id"])

    if text.startswith("/start"):
      web_app_url = "https://smm-botbd.onrender.com"
      payload = {
          "chat_id": chat_id,
          "text": (
              "আসসালামু আলাইকুম বদ্দা! আমাদের অফিশিয়াল SMM প্যানেল মিনি অ্যাপে"
              " স্বাগতম। নিচে ক্লিক করে অর্ডার করো:"
          ),
          "reply_markup": {
              "inline_keyboard": [[{
                  "text": "🚀 এসএসএম প্যানেল মিনি অ্যাপ ওপেন করো",
                  "web_app": {"url": web_app_url},
              }]]
          },
      }
      requests.post(
          f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload
      )

    # অ্যাডমিনের জন্য ব্যালেন্স এপ্রুভ করার কমান্ড: /addbal <user_id> <amount>
    elif text.startswith("/addbal") and str(chat_id) == str(ADMIN_CHAT_ID):
      parts = text.split()
      if len(parts) == 3:
        target_user = parts[1]
        add_amount = float(parts[2])
        db = load_db()
        if target_user not in db:
          db[target_user] = {"balance": 0.0}
        db[target_user]["balance"] += add_amount
        save_db(db)

        # ইউজারকে জানানো
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": target_user,
                "text": (
                    f"আলহামদুলিল্লাহ বদ্দা! তোর একাউন্টে ৳{add_amount} যোগ করা"
                    " হয়েছে।"
                ),
            },
        )
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": (
                    f"সফল! ইউজার {target_user}-কে ৳{add_amount} ব্যালেন্স দেওয়া"
                    " হয়েছে।"
                ),
            },
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
