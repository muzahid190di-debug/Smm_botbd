import os
import json
import requests
from flask import Flask, render_template_string, request

# ==================== সিস্টেম ও এপিআই কনফিগারেশন ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "7688292665:AAHIADDH-V59bpL067QmxW5w67SrYLLwpz0")
SMM_API_KEY = os.environ.get("SMM_API_KEY", "YOUR_ACTUAL_SMM_API_KEY")
SMM_API_URL = "https://bdsmmpanel.com/api/v2"

# টেলিগ্রাম অ্যাডমিন চ্যাট আইডি
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "YOUR_TELEGRAM_ADMIN_CHAT_ID")
DB_FILE = "users_db.json"

# ==================== ফাইল ডাটাবেজ হেলপার ====================
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_db(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print("Database Save Error:", e)

# ==================== SMM API থেকে লাইভ ডাটা ফেচিং ====================
def get_smm_services():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'application/json'
    }
    payload = {
        'key': SMM_API_KEY,
        'action': 'services'
    }
    
    try:
        response = requests.post(SMM_API_URL, data=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                formatted_services = {}
                for s in data:
                    try:
                        orig_rate = float(s.get('rate', 0))
                        
                        # ডায়নামিক প্রফিট মার্জিন হিসাব
                        if orig_rate <= 10:
                            profit = 5
                        elif orig_rate <= 50:
                            profit = 15
                        elif orig_rate <= 150:
                            profit = 25
                        else:
                            profit = 40
                        
                        final_price = round(orig_rate + profit, 2)
                        cat_name = s.get('category', 'General Services').strip()
                        service_id = str(s.get('service'))

                        formatted_services[service_id] = {
                            "id": service_id,
                            "name": s.get('name', 'Service ' + service_id),
                            "category": cat_name,
                            "price_per_1k": final_price,
                            "min": int(s.get('min', 10)),
                            "max": int(s.get('max', 100000))
                        }
                    except (ValueError, TypeError):
                        continue
                if formatted_services:
                    return formatted_services
    except Exception as err:
        print("SMM API Connection Error:", err)

    # এপিআই ব্যর্থতায় ডিফল্ট ডামি ডাটা
    return {
        "29894": {
            "id": "29894",
            "name": "Spotify Followers | Instant Start | Real User",
            "category": "Spotify Followers | Artist | User",
            "price_per_1k": 125.0,
            "min": 50,
            "max": 10000
        },
        "102": {
            "id": "102",
            "name": "Facebook Profile Followers | Non Drop 30 Days Refill",
            "category": "Facebook Followers / Page Likes",
            "price_per_1k": 140.0,
            "min": 100,
            "max": 50000
        }
    }

app = Flask(__name__)

# ==================== ফ্রন্টএন্ড মিনি অ্যাপ ইন্টারফেস ====================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SMM Panel Store</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        :root {
            --bg-color: #f0f4f8;
            --card-bg: #ffffff;
            --text-color: #1e293b;
            --text-muted: #64748b;
            --primary: #0284c7;
            --primary-light: #e0f2fe;
            --border: #e2e8f0;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 12px;
            box-sizing: border-box;
        }

        .container { max-width: 480px; margin: 0 auto; }

        .balance-card {
            background: linear-gradient(135deg, #0284c7, #2563eb);
            color: #ffffff;
            border-radius: 16px;
            padding: 18px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(2, 132, 199, 0.2);
            margin-bottom: 14px;
        }

        .balance-title { font-size: 13px; opacity: 0.9; text-transform: uppercase; letter-spacing: 0.5px; }
        .balance-amount { font-size: 30px; font-weight: 800; margin-top: 4px; }

        .navigation-tabs {
            display: flex;
            background: #ffffff;
            border-radius: 12px;
            padding: 4px;
            margin-bottom: 14px;
            border: 1px solid var(--border);
        }

        .tab-btn {
            flex: 1;
            padding: 10px;
            border: none;
            background: transparent;
            color: var(--text-muted);
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .tab-btn.active { background: var(--primary); color: #ffffff; }

        .panel-card {
            background: var(--card-bg);
            border-radius: 16px;
            padding: 16px;
            border: 1px solid var(--border);
            box-shadow: 0 4px 12px rgba(0,0,0,0.03);
            margin-bottom: 14px;
        }

        .platform-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 8px;
            margin-bottom: 14px;
        }

        .platform-icon {
            background: #f8fafc;
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 10px 0;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 18px;
            color: var(--text-muted);
        }

        .platform-icon.active {
            border-color: var(--primary);
            color: var(--primary);
            background: var(--primary-light);
        }

        .input-group { margin-bottom: 12px; }

        .input-group label {
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: var(--text-muted);
            margin-bottom: 6px;
            text-transform: uppercase;
        }

        .form-control {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border);
            border-radius: 10px;
            background: #f8fafc;
            font-size: 14px;
            color: var(--text-color);
            box-sizing: border-box;
            outline: none;
        }

        .form-control:focus { border-color: var(--primary); background: #ffffff; }

        .badge-info { font-size: 11px; color: #d97706; margin-top: 4px; font-weight: 600; }

        .total-box {
            background: var(--primary-light);
            color: var(--primary);
            padding: 12px;
            border-radius: 10px;
            text-align: center;
            font-size: 16px;
            font-weight: 700;
            margin-top: 14px;
        }

        .btn-submit {
            width: 100%;
            background: var(--primary);
            color: #ffffff;
            border: none;
            padding: 14px;
            border-radius: 10px;
            font-size: 15px;
            font-weight: 700;
            margin-top: 14px;
            cursor: pointer;
        }

        .bkash-container {
            background: #fdf2f8;
            border: 1px dashed #f43f5e;
            padding: 14px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 12px;
        }

        .bkash-number { font-size: 18px; font-weight: 800; color: #be123c; margin-top: 4px; }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="container">
        <div class="balance-card">
            <div class="balance-title">বর্তমান ওয়ালেট ব্যালেন্স</div>
            <div class="balance-amount">৳ <span id="userBalance">0.00</span></div>
        </div>

        <div class="navigation-tabs">
            <button class="tab-btn active" onclick="switchTab('order')">অর্ডার করুন</button>
            <button class="tab-btn" onclick="switchTab('deposit')">ব্যালেন্স রিচার্জ</button>
        </div>

        <!-- অর্ডার সেকশন -->
        <div id="orderTab" class="panel-card">
            <div class="platform-grid">
                <div class="platform-icon active" onclick="filterPlatform('all', this)"><i class="fa-solid fa-house"></i></div>
                <div class="platform-icon" onclick="filterPlatform('facebook', this)"><i class="fa-brands fa-facebook"></i></div>
                <div class="platform-icon" onclick="filterPlatform('youtube', this)"><i class="fa-brands fa-youtube"></i></div>
                <div class="platform-icon" onclick="filterPlatform('instagram', this)"><i class="fa-brands fa-instagram"></i></div>
                <div class="platform-icon" onclick="filterPlatform('telegram', this)"><i class="fa-brands fa-telegram"></i></div>
                <div class="platform-icon" onclick="filterPlatform('tiktok', this)"><i class="fa-brands fa-tiktok"></i></div>
                <div class="platform-icon" onclick="filterPlatform('spotify', this)"><i class="fa-brands fa-spotify"></i></div>
                <div class="platform-icon" onclick="filterPlatform('twitter', this)"><i class="fa-brands fa-x-twitter"></i></div>
                <div class="platform-icon" onclick="filterPlatform('linkedin', this)"><i class="fa-brands fa-linkedin"></i></div>
                <div class="platform-icon" onclick="filterPlatform('discord', this)"><i class="fa-brands fa-discord"></i></div>
            </div>

            <div class="input-group">
                <label>১. ক্যাটাগরি নির্বাচন করুন</label>
                <select id="categorySelect" class="form-control" onchange="onCategoryChange()"></select>
            </div>

            <div class="input-group">
                <label>২. নির্দিষ্ট সার্ভিস বেছে নিন</label>
                <select id="serviceSelect" class="form-control" onchange="onServiceChange()"></select>
                <div class="badge-info" id="limitBadge">সর্বনিম্ন: 0 | সর্বোচ্চ: 0</div>
            </div>

            <div class="input-group">
                <label>৩. টার্গেট লিঙ্ক (URL)</label>
                <input type="text" id="targetLink" class="form-control" placeholder="https://..." />
            </div>

            <div class="input-group">
                <label>৪. পরিমাণ (Quantity)</label>
                <input type="number" id="orderQuantity" class="form-control" value="1000" oninput="calculateTotal()" />
            </div>

            <div class="total-box" id="totalCostDisplay">মোট মূল্য: ৳0.00</div>
            <button class="btn-submit" onclick="processOrder()">অর্ডার কনফার্ম করুন</button>
        </div>

        <!-- রিচার্জ সেকশন -->
        <div id="depositTab" class="panel-card hidden">
            <div class="bkash-container">
                <div style="font-size: 12px; color: #9f1239;">বিকাশ পার্সোনাল নম্বর (Send Money):</div>
                <div class="bkash-number">01605969856</div>
            </div>

            <div class="input-group">
                <label>টাকার পরিমাণ (সর্বনিম্ন ৳১০)</label>
                <input type="number" id="depositAmount" class="form-control" placeholder="১০" min="10" />
            </div>

            <div class="input-group">
                <label>বিকাশ ট্রানজেকশন আইডি (TrxID)</label>
                <input type="text" id="depositTrx" class="form-control" placeholder="9N7X..." />
            </div>

            <button class="btn-submit" onclick="processDeposit()">পেমেন্ট তথ্য সাবমিট করুন</button>
        </div>
    </div>

    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const userId = tg.initDataUnsafe?.user?.id || "12345678";
        const userFirstName = tg.initDataUnsafe?.user?.first_name || "User";
        const servicesData = {{ services | tojson }};

        function fetchUserBalance() {
            fetch('/get_balance?user_id=' + userId)
                .then(r => r.json())
                .then(d => {
                    document.getElementById('userBalance').innerText = d.balance.toFixed(2);
                });
        }

        function filterPlatform(platform, element) {
            document.querySelectorAll('.platform-icon').forEach(i => i.classList.remove('active'));
            element.classList.add('active');

            const catSelect = document.getElementById('categorySelect');
            catSelect.innerHTML = "";

            const categories = [...new Set(Object.values(servicesData).map(s => s.category))];
            let addedCount = 0;

            categories.forEach(cat => {
                if(platform === 'all' || cat.toLowerCase().includes(platform)) {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    opt.innerText = cat;
                    catSelect.appendChild(opt);
                    addedCount++;
                }
            });

            if(addedCount === 0) {
                categories.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    opt.innerText = cat;
                    catSelect.appendChild(opt);
                });
            }
            onCategoryChange();
        }

        function onCategoryChange() {
            const selectedCat = document.getElementById('categorySelect').value;
            const servSelect = document.getElementById('serviceSelect');
            servSelect.innerHTML = "";

            for(const [sId, s] of Object.entries(servicesData)) {
                if(s.category === selectedCat) {
                    const opt = document.createElement('option');
                    opt.value = sId;
                    opt.innerText = `${s.id} - ${s.name} (৳${s.price_per_1k}/1k)`;
                    opt.setAttribute('data-price', s.price_per_1k);
                    opt.setAttribute('data-min', s.min);
                    opt.setAttribute('data-max', s.max);
                    servSelect.appendChild(opt);
                }
            }
            onServiceChange();
        }

        function onServiceChange() {
            const servSelect = document.getElementById('serviceSelect');
            const selected = servSelect.options[servSelect.selectedIndex];
            if(selected) {
                const min = selected.getAttribute('data-min');
                const max = selected.getAttribute('data-max');
                document.getElementById('limitBadge').innerText = `সর্বনিম্ন: ${min} | সর্বোচ্চ: ${max}`;
            }
            calculateTotal();
        }

        function calculateTotal() {
            const servSelect = document.getElementById('serviceSelect');
            const selected = servSelect.options[servSelect.selectedIndex];
            if(!selected) return;

            const price = parseFloat(selected.getAttribute('data-price'));
            const qty = parseFloat(document.getElementById('orderQuantity').value) || 0;
            const total = (qty / 1000) * price;
            document.getElementById('totalCostDisplay').innerText = "মোট মূল্য: ৳" + total.toFixed(2);
        }

        function switchTab(tabName) {
            if(tabName === 'order') {
                document.getElementById('orderTab').classList.remove('hidden');
                document.getElementById('depositTab').classList.add('hidden');
                document.querySelectorAll('.tab-btn')[0].classList.add('active');
                document.querySelectorAll('.tab-btn')[1].classList.remove('active');
            } else {
                document.getElementById('orderTab').classList.add('hidden');
                document.getElementById('depositTab').classList.remove('hidden');
                document.querySelectorAll('.tab-btn')[1].classList.add('active');
                document.querySelectorAll('.tab-btn')[0].classList.remove('active');
            }
        }

        function processOrder() {
            const serviceId = document.getElementById('serviceSelect').value;
            const link = document.getElementById('targetLink').value;
            const quantity = parseInt(document.getElementById('orderQuantity').value);
            const selectedOpt = document.getElementById('serviceSelect').selectedOptions[0];

            if(!selectedOpt || !link || !quantity) {
                alert("অনুগ্রহ করে সকল তথ্য সঠিকভাবে প্রদান করুন!");
                return;
            }

            const min = parseInt(selectedOpt.getAttribute('data-min'));
            const max = parseInt(selectedOpt.getAttribute('data-max'));

            if(quantity < min || quantity > max) {
                alert(`পরিমাণ অবশ্যই ${min} থেকে ${max}-এর মধ্যে হতে হবে!`);
                return;
            }

            fetch('/api/order', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, service_id: serviceId, link: link, quantity: quantity })
            })
            .then(r => r.json())
            .then(d => {
                alert(d.message);
                if(d.success) fetchUserBalance();
            });
        }

        function processDeposit() {
            const amount = parseFloat(document.getElementById('depositAmount').value);
            const trxId = document.getElementById('depositTrx').value.trim();

            if(!amount || amount < 10 || !trxId) {
                alert("ন্যূনতম ৳১০ এবং সঠিক ট্রানজেকশন আইডি প্রদান করুন!");
                return;
            }

            fetch('/api/deposit', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: userId, first_name: userFirstName, amount: amount, trx_id: trxId })
            })
            .then(r => r.json())
            .then(d => {
                alert(d.message);
                if(d.success) tg.close();
            });
        }

        filterPlatform('all', document.querySelectorAll('.platform-icon')[0]);
        fetchUserBalance();
    </script>
</body>
</html>
"""

# ==================== এন্ডপয়েন্ট হ্যান্ডলারসমূহ ====================
@app.route("/")
def index_route():
    services = get_smm_services()
    return render_template_string(HTML_TEMPLATE, services=services)

@app.route("/get_balance")
def get_balance_route():
    user_id = str(request.args.get("user_id"))
    db = load_db()
    balance = db.get(user_id, {}).get("balance", 0.0)
    return {"balance": balance}

@app.route("/api/order", methods=["POST"])
def order_route():
    data = request.json or {}
    user_id = str(data.get("user_id"))
    service_id = str(data.get("service_id"))
    link = data.get("link")
    quantity = int(data.get("quantity", 0))

    services = get_smm_services()
    if service_id not in services:
        return {"success": False, "message": "নির্বাচিত সার্ভিসটি বর্তমানে অনুপলব্ধ!"}

    serv = services[service_id]
    total_cost = (quantity / 1000.0) * serv["price_per_1k"]

    db = load_db()
    if user_id not in db:
        db[user_id] = {"balance": 0.0}

    if db[user_id]["balance"] < total_cost:
        return {"success": False, "message": "আপনার ওয়ালেটে পর্যাপ্ত ব্যালেন্স নেই! রিচার্জ করুন।"}

    # SMM API-তে অর্ডার পাঠানো
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    payload = {
        'key': SMM_API_KEY,
        'action': 'add',
        'service': service_id,
        'link': link,
        'quantity': quantity
    }
    
    try:
        res = requests.post(SMM_API_URL, data=payload, headers=headers, timeout=12).json()
        if "order" in res:
            db[user_id]["balance"] -= total_cost
            save_db(db)
            return {"success": True, "message": f"অর্ডার সফল হয়েছে! অর্ডার আইডি: {res['order']}"}
        else:
            return {"success": False, "message": f"অর্ডার ব্যর্থ হয়েছে: {res.get('error', 'API সমস্যা')}"}
    except Exception:
        return {"success": False, "message": "সার্ভার কানেকশন সমস্যা। পরে চেষ্টা করুন।"}

@app.route("/api/deposit", methods=["POST"])
def deposit_route():
    data = request.json or {}
    user_id = str(data.get("user_id"))
    first_name = data.get("first_name", "User")
    amount = float(data.get("amount", 0))
    trx_id = data.get("trx_id")

    if ADMIN_CHAT_ID and ADMIN_CHAT_ID != "YOUR_TELEGRAM_ADMIN_CHAT_ID":
        msg = f"🔔 **নতুন রিচার্জ অনুরোধ!**\n\n👤 ব্যবহারকারী: {first_name}\n🆔 আইডি: `{user_id}`\n💰 পরিমাণ: ৳{amount}\n💳 TrxID: `{trx_id}`"
        keyboard = {
            "inline_keyboard": [[
                {"text": f"✅ এপ্রুভ করুন (৳{amount})", "callback_data": f"approve_{user_id}_{amount}"}
            ]]
        }
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": ADMIN_CHAT_ID,
                "text": msg,
                "parse_mode": "Markdown",
                "reply_markup": keyboard
            }, timeout=8)
        except Exception:
            pass

    return {"success": True, "message": "পেমেন্ট তথ্য সাবমিট হয়েছে! যাচাই শেষে ব্যালেন্স যোগ হবে।"}

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json() or {}

    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        if text.startswith("/start"):
            web_app_url = "https://smm-botbd.onrender.com"
            payload = {
                "chat_id": chat_id,
                "text": "আসসালামু আলাইকুম!\n\nআমাদের অফিশিয়াল SMM প্যানেলে আপনাকে স্বাগতম। সেবা নিতে নিচের বোতামে চাপ দিন:",
                "reply_markup": {
                    "inline_keyboard": [[
                        {"text": "🚀 SMM প্যানেল খুলুন", "web_app": {"url": web_app_url}}
                    ]]
                }
            }
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json=payload)

    elif "callback_query" in data:
        cq = data["callback_query"]
        cq_id = cq["id"]
        data_val = cq.get("data", "")
        admin_chat_id = cq["message"]["chat"]["id"]

        if data_val.startswith("approve_"):
            _, target_user, add_amount = data_val.split("_")
            add_amount = float(add_amount)

            db = load_db()
            if target_user not in db:
                db[target_user] = {"balance": 0.0}
            db[target_user]["balance"] += add_amount
            save_db(db)

            # ব্যবহারকারীকে মেসেজ পাঠানো
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": target_user,
                "text": f"আপনার অ্যাকাউন্টে ৳{add_amount} সফলভাবে যোগ করা হয়েছে।"
            })

            # অ্যাডমিন নোটিফিকেশন আপডেট
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={
                "chat_id": admin_chat_id,
                "text": f"✅ অ্যাকাউন্ট `{target_user}`-এ ৳{add_amount} অনুমোদন করা হয়েছে।"
            })

            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answercallbackquery", json={
                "callback_query_id": cq_id,
                "text": "অনুমোদিত হয়েছে!"
            })

    return "OK", 200

def set_webhook():
    if BOT_TOKEN and "YOUR" not in BOT_TOKEN:
        webhook_url = f"https://smm-botbd.onrender.com/{BOT_TOKEN}"
        try:
            requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}", timeout=8)
        except Exception:
            pass

if __name__ == "__main__":
    set_webhook()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
