import requests
from bs4 import BeautifulSoup
import re

def parse_specs(title, brand, series_num):
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
            # Look for standalone storage numbers
            val_match = re.search(r'\b(128|256|512)\b(?!.*(?:gb|tb))', title_lower)
            storage = f"{val_match.group(1)}GB" if val_match else "Unknown Storage"
            
    # 3. Determine RAM
    ram = ""
    if brand == "google":
        ram_match = re.search(r'\b(6|8|12|16|24)\s*gb\s*ram\b', title_lower)
        if not ram_match:
            ram_match = re.search(r'\b(6|8|12|16|24)\s*gb\s*[\+/]\s*(?:128|256|512)\s*gb\b', title_lower)
            if not ram_match:
                # Standalone GB if different from storage
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

def test():
    devices = [
        {"query": "google pixel 10", "brand": "google", "pattern": r'\bpixel\s+10\w*\b', "series": 10},
        {"query": "iphone 15", "brand": "apple", "pattern": r'\biphone\s+15\w*\b', "series": 15},
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for dev in devices:
        query = dev["query"]
        pattern = dev["pattern"]
        url = f'https://www.jumia.com.ng/smartphones/?q={query.replace(" ", "+")}'
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        products = soup.select('article.prd')
        
        configs = {}
        for p in products:
            name_el = p.select_one('.name')
            price_el = p.select_one('.prc')
            if name_el and price_el:
                name = name_el.text.strip()
                name_lower = name.lower()
                
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
                    
                    if price_num >= 150000:
                        sub_type, storage, ram = parse_specs(name, dev["brand"], dev["series"])
                        config_key = f"{sub_type} - {storage}"
                        if ram:
                            config_key += f" ({ram})"
                            
                        # If configuration already found, keep the lowest price
                        if config_key not in configs or price_num < configs[config_key]["price"]:
                            configs[config_key] = {
                                "price": price_num,
                                "price_formatted": price_text,
                                "name": name
                            }
                            
        print(f"=== CONFIGURATIONS FOR {query.upper()} ===")
        for cfg, data in sorted(configs.items()):
            print(f"- {cfg} -> {data['price_formatted'].replace('₦', 'NGN')} (Listing: {data['name']})")
        print()

if __name__ == "__main__":
    test()
