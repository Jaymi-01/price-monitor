import os
import re
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# Load configuration from .env file
load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

HISTORY_FILE = "price_history.json"

# Target device series to monitor
MONITORED_DEVICES = [
    {"id": "pixel_10", "display_name": "Google Pixel 10 Series", "brand": "google", "pattern": r'\bpixel\s+10\w*\b', "series": 10, "query": "google pixel 10"},
    {"id": "pixel_11", "display_name": "Google Pixel 11 Series", "brand": "google", "pattern": r'\bpixel\s+11\w*\b', "series": 11, "query": "google pixel 11"},
    {"id": "iphone_15", "display_name": "iPhone 15 Series", "brand": "apple", "pattern": r'\biphone\s+15\w*\b', "series": 15, "query": "iphone 15"},
    {"id": "iphone_16", "display_name": "iPhone 16 Series", "brand": "apple", "pattern": r'\biphone\s+16\w*\b', "series": 16, "query": "iphone 16"},
    {"id": "iphone_17", "display_name": "iPhone 17 Series", "brand": "apple", "pattern": r'\biphone\s+17\w*\b', "series": 17, "query": "iphone 17"},
]

def send_html_email(subject, html_body):
    """Sends a styled HTML email notification via SMTP."""
    if not all([SENDER_EMAIL, SENDER_PASSWORD, RECEIVER_EMAIL, SMTP_SERVER, SMTP_PORT]) or \
       "your-email" in SENDER_EMAIL or "your-app-password" in SENDER_PASSWORD:
        print("[WARNING] Email notification skipped: SMTP configuration is incomplete or contains placeholder values in .env.")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        # Secure connection to the SMTP server
        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()

        print(f"[SUCCESS] Price report email successfully sent to {RECEIVER_EMAIL}!")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email: {e}")
        return False

def parse_specs(title, brand, series_num):
    """Parses model sub-type, storage, and RAM specs from the product title."""
    title_lower = title.lower()
    
    # 1. Determine Model Sub-type
    sub_type = "Base"
    if "pro max" in title_lower or "promax" in title_lower:
        sub_type = "Pro Max"
    elif "pro xl" in title_lower or "proxl" in title_lower:
        sub_type = "Pro XL"
    elif "pro fold" in title_lower or "fold" in title_lower:
        sub_type = "Pro Fold"
    elif "pro" in title_lower:
        sub_type = "Pro"
    elif "plus" in title_lower:
        sub_type = "Plus"
    elif f"{series_num}a" in title_lower:
        sub_type = f"{series_num}a"
        
    # 2. Determine Storage (ROM)
    storage_match = re.search(r'\b(128|256|512)\s*gb\b', title_lower)
    if not storage_match:
        storage_match = re.search(r'\b1\s*tb\b', title_lower)
        
    if storage_match:
        storage = storage_match.group(0).upper().replace(" ", "")
    else:
        rom_match = re.search(r'\b(128|256|512|1000)\s*(?:rom|gb\s*rom)\b', title_lower)
        if rom_match:
            val = rom_match.group(1)
            storage = "1TB" if val == "1000" else f"{val}GB"
        else:
            # Standalone storage match (e.g. "iphone 15 128")
            val_match = re.search(r'\b(128|256|512)\b(?!.*(?:gb|tb))', title_lower)
            storage = f"{val_match.group(1)}GB" if val_match else "Unknown Storage"
            
    # 3. Determine RAM
    ram = ""
    if brand == "google":
        ram_match = re.search(r'\b(6|8|12|16|24)\s*gb\s*ram\b', title_lower)
        if not ram_match:
            ram_match = re.search(r'\b(6|8|12|16|24)\s*gb\s*[\+/]\s*(?:128|256|512)\s*gb\b', title_lower)
            if not ram_match:
                # Standalone RAM match (e.g., "12GB" separate from storage size)
                standalone_matches = re.findall(r'\b(6|8|12|16|24)\s*gb\b', title_lower)
                for val in standalone_matches:
                    if f"{val}GB" != storage:
                        ram = f"{val}GB RAM"
                        break
        if ram_match and not ram:
            ram = f"{ram_match.group(1)}GB RAM"
        if not ram:
            ram = "Unknown RAM"
            
    return sub_type, storage, ram

def scrape_jumia_prices(device):
    """Searches Jumia for a device series and groups by configuration (specs)."""
    query = device["query"]
    pattern = device["pattern"]
    brand = device["brand"]
    series_num = device["series"]
    
    url = f'https://www.jumia.com.ng/smartphones/?q={query.replace(" ", "+")}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    print(f"[INFO] Scraping and parsing details for: {query}...")
    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Request failed for {query}: {e}")
        return None

    soup = BeautifulSoup(r.text, 'html.parser')
    products = soup.select('article.prd')
    
    configs = {}
    for p in products:
        name_el = p.select_one('.name')
        price_el = p.select_one('.prc')
        
        if name_el and price_el:
            name = name_el.text.strip()
            name_lower = name.lower()
            
            # Exclude accessories and fake/converted products
            exclusions = [
                "case", "cover", "protector", "glass", "lens", "cable", "charger", 
                "guard", "stripe", "strap", "film", "converted", "cloned", "dummy", 
                "replica", "box only", "housing", "shell", "sticker", "decal", "skin"
            ]
            if any(exc in name_lower for exc in exclusions):
                continue
            
            if re.search(pattern, name_lower):
                price_text = price_el.text.strip()
                price_num = int(re.sub(r'[^\d]', '', price_text)) if re.sub(r'[^\d]', '', price_text) else 0
                
                # Minimum phone price floor
                if price_num >= 150000:
                    sub_type, storage, ram = parse_specs(name, brand, series_num)
                    
                    # Generate a unique configuration key
                    config_key = f"{sub_type} - {storage}"
                    if ram:
                        config_key += f" ({ram})"
                    
                    # Resolve product landing link
                    link_el = p.select_one('a.core')
                    path = link_el['href'] if link_el and 'href' in link_el.attrs else ""
                    full_link = f"https://www.jumia.com.ng{path}" if path.startswith('/') else path
                    
                    # Store the lowest priced listing for this configuration
                    if config_key not in configs or price_num < configs[config_key]["price"]:
                        configs[config_key] = {
                            "price": price_num,
                            "formatted_price": price_text,
                            "name": name,
                            "link": full_link
                        }
                        
    return {
        "search_url": url,
        "configs": configs
    }

def load_history():
    """Loads historical prices from the local database file."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("[WARNING] Price history file was corrupted. Re-initializing.")
            return {}
    return {}

def save_history(history):
    """Saves the price history database."""
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=4)

def format_naira(amount):
    """Formats raw integers as Naira currency strings."""
    return f"N{amount:,}"

def generate_report_html(current_data, last_configs_all, has_changes):
    """Generates a premium, responsive card-based HTML email report."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    html = f"""
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #2c3e50; margin: 0; padding: 20px; background-color: #f6f8fa; }}
        .container {{ max-width: 600px; background: #ffffff; margin: 0 auto; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); overflow: hidden; border: 1px solid #e1e4e8; }}
        .header {{ background: #1c1c1e; color: #ffffff; padding: 24px 20px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }}
        .header p {{ margin: 6px 0 0 0; font-size: 12px; color: #a1a1a6; }}
        .content {{ padding: 20px; }}
        .status-bar {{ padding: 12px; border-radius: 8px; margin-bottom: 24px; font-size: 13px; font-weight: 600; text-align: center; }}
        .status-alert {{ background: #fff8e1; color: #b78103; border: 1px solid #ffe082; }}
        .status-ok {{ background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }}
        
        .series-section {{ margin-bottom: 30px; }}
        .series-title {{ font-size: 16px; font-weight: 700; color: #1c1c1e; border-left: 4px solid #0076f6; padding-left: 10px; margin-bottom: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
        
        .card {{ background: #fafafa; border: 1px solid #e1e4e8; border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
        .card-table {{ width: 100%; border-collapse: collapse; border: none; }}
        .config-name {{ font-size: 15px; font-weight: 700; color: #1c1c1e; }}
        
        .price-badge {{ font-size: 13px; font-weight: 700; padding: 4px 8px; border-radius: 6px; display: inline-block; }}
        .price {{ background: #f0f3f6; color: #1c1c1e; }}
        .price-drop {{ background: #e8f5e9; color: #2e7d32; }}
        .price-up {{ background: #ffebee; color: #c62828; }}
        .price-new {{ background: #dbedff; color: #0366d6; }}
        
        .price-diff {{ font-size: 10px; display: block; color: #6a737d; margin-top: 2px; text-align: right; }}
        .product-desc {{ font-size: 12px; color: #586069; line-height: 1.5; word-break: break-word; }}
        
        .deal-btn {{ display: inline-block; background: #1c1c1e; color: #ffffff !important; text-decoration: none; padding: 6px 14px; border-radius: 6px; font-size: 11px; font-weight: 700; border: 1px solid #1c1c1e; }}
        .deal-btn:hover {{ background: #000000; }}
        .footer {{ background: #f6f8fa; text-align: center; padding: 20px; font-size: 11px; color: #6a737d; border-top: 1px solid #e1e4e8; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>📱 Smartphone Price Spec Monitor</h1>
          <p>Scraped from Jumia Nigeria on {timestamp}</p>
        </div>
        <div class="content">
          <div class="status-bar { 'status-alert' if has_changes else 'status-ok' }">
            { '⚠️ Notice: Price changes or new listings detected!' if has_changes else '✅ All monitored smartphone configurations are at baseline prices.' }
          </div>
    """
    
    for dev in MONITORED_DEVICES:
        dev_id = dev["id"]
        status = current_data.get(dev_id)
        last_configs = last_configs_all.get(dev_id, {})
        
        html += f"""
        <div class="series-section">
          <div class="series-title">{dev["display_name"]}</div>
        """
        
        if not status or not status["configs"]:
            html += f"""
            <div style="color:#8c8c8c; font-style:italic; font-size:12px; padding: 8px 10px; background: #fafafa; border-radius: 6px; border: 1px dashed #e1e4e8;">
              Out of stock or no listings available.
            </div>
            </div>
            """
            continue
            
        # Sort configurations by name
        for config_key, item in sorted(status["configs"].items()):
            price = item["price"]
            last_price = last_configs.get(config_key)
            
            # Determine styling status
            price_class = "price"
            diff_text = ""
            
            if last_price is None:
                if last_configs_all: 
                    price_class = "price-new"
                    diff_text = "New Listing"
            else:
                diff = price - last_price
                if diff < 0:
                    price_class = "price-drop"
                    diff_text = f"📉 Saved {format_naira(abs(diff))}"
                elif diff > 0:
                    price_class = "price-up"
                    diff_text = f"📈 Rose {format_naira(diff)}"
            
            html += f"""
            <div class="card">
              <table class="card-table">
                <tr>
                  <td style="padding: 0 0 8px 0; text-align: left;">
                    <span class="config-name">{config_key}</span>
                  </td>
                  <td style="padding: 0 0 8px 0; text-align: right; vertical-align: top;">
                    <span class="price-badge {price_class}">{format_naira(price)}</span>
                    {f'<span class="price-diff">{diff_text}</span>' if diff_text else ''}
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding: 4px 0 12px 0; text-align: left;">
                    <div class="product-desc">{item['name']}</div>
                  </td>
                </tr>
                <tr>
                  <td colspan="2" style="padding: 0; text-align: left;">
                    <a href="{item['link']}" class="deal-btn">View on Jumia &rarr;</a>
                  </td>
                </tr>
              </table>
            </div>
            """
            
        html += """
        </div>
        """
        
    html += """
        </div>
        <div class="footer">
          <p>This is an automated report from your Jumia Price Scraper pipeline.</p>
          <p>To configure your schedule, modify your Windows Task Scheduler or GitHub Actions workflow.</p>
        </div>
      </div>
    </body>
    </html>
    """
    return html

def run_pipeline():
    """Executes the price monitor pipeline."""
    print("--- Starting Phone Specification Price Monitor Pipeline ---")
    
    current_runs = {}
    history = load_history()
    
    # Check if historical schema has configs, if not re-initialize
    if "configs" not in history:
        history["configs"] = {}
        
    last_configs_all = history.get("configs", {})
    
    # Scrape each device series
    for dev in MONITORED_DEVICES:
        data = scrape_jumia_prices(dev)
        if data:
            current_runs[dev["id"]] = data
            print(f"[FOUND] {dev['display_name']} -> Parsed {len(data['configs'])} distinct configurations.")
        else:
            current_runs[dev["id"]] = None
            
    # Compare current run prices against historical specs prices
    has_changes = False
    is_first_run = len(last_configs_all) == 0
    
    new_configs_all = {}
    for dev in MONITORED_DEVICES:
        dev_id = dev["id"]
        status = current_runs[dev_id]
        
        new_configs_all[dev_id] = {}
        if status:
            for config_key, item in status["configs"].items():
                price = item["price"]
                new_configs_all[dev_id][config_key] = price
                
                # Check for changes
                last_price = last_configs_all.get(dev_id, {}).get(config_key)
                if last_price is not None and price != last_price:
                    has_changes = True
                elif last_price is None and last_configs_all:
                    # New config introduced
                    has_changes = True
        
        # Check if configurations went out of stock
        for config_key in last_configs_all.get(dev_id, {}):
            if config_key not in new_configs_all[dev_id]:
                has_changes = True # A configuration vanished (out of stock)
                
    # Update and save history log
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history["last_checked"] = timestamp
    history["configs"] = new_configs_all
    
    if "logs" not in history:
        history["logs"] = []
    history["logs"].append({
        "timestamp": timestamp,
        "configs": new_configs_all
    })
    
    save_history(history)
    
    # Email alert decision logic
    if is_first_run:
        print("[INFO] First run: sending baseline spec price report email.")
        subject = "🔔 Phone Price Spec Monitor Started (Baseline Report)"
        html_report = generate_report_html(current_runs, {}, False)
        send_html_email(subject, html_report)
    elif has_changes:
        print("[ALERT] Price changes/new configs detected! Sending alert email.")
        subject = "🔥 ALERT: Smartphone spec prices updated in Nigeria!"
        html_report = generate_report_html(current_runs, last_configs_all, True)
        send_html_email(subject, html_report)
    else:
        print("[INFO] No spec price changes detected. Email report skipped.")

if __name__ == "__main__":
    run_pipeline()
