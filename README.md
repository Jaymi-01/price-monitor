# 📱 Tech Price Monitor Pipeline (Nigeria)

An automated Python scraping pipeline that monitors online listings on Jumia Nigeria for flagship smartphones, tracks price drops, and sends beautiful HTML email notifications in Naira (NGN).

## 🚀 Tracked Devices

The scraper is pre-configured to track the following smartphone series:
*   **Google Pixel 10 Series** (Pixel 10, Pixel 10a, Pixel 10 Pro, Pixel 10 Pro XL, Pixel 10 Pro Fold)
*   **Google Pixel 11 Series**
*   **iPhone 15 Series** (iPhone 15, 15 Plus, 15 Pro, 15 Pro Max)
*   **iPhone 16 Series** (iPhone 16, 16 Plus, 16 Pro, 16 Pro Max)
*   **iPhone 17 Series**

### Anti-Noise Filtration
To ensure accuracy, the scraper automatically filters out:
1.  **Accessories:** Cases, screen protectors, cables, chargers, shells, and skins.
2.  **Mockups & Fakes:** "Converted" or "cloned" model listings.
3.  **Irrelevant matches:** Items below ₦150,000 (which are usually cases or chargers showing up in results).

---

## 🏃 Setup and Execution

### 1. Install Dependencies
Run this command in the project directory to install the required packages:
```bash
pip install -r requirements.txt
```

### 2. Run the Scraper Manually
```bash
.venv\Scripts\python scraper.py
```

### 3. Price History Logging
All data is stored inside [`price_history.json`](price_history.json). It logs:
*   `last_checked`: Timestamp of the last run.
*   `lowest_prices`: A mapping of each device series to its lowest detected price.
*   `logs`: A historical run log showing price trends over time.

---

## 📧 Email Alerts Setup

The script automatically detects if your system has email environment variables configured. If not, copy the environment settings or configure your [`.env`](.env) file:
*   `SMTP_SERVER` / `SMTP_PORT`: (e.g., `smtp.gmail.com` on port `587`)
*   `SENDER_EMAIL` / `SENDER_PASSWORD`: Your email address and a secure **App Password** (mandatory for Google accounts).
*   `RECEIVER_EMAIL`: Where you want the alerts sent.

---

## 🤖 Automating the Pipeline

### Windows Task Scheduler (Local)
To check prices automatically every morning:
1.  Open **Task Scheduler** on Windows.
2.  Click **Create Basic Task** and set the trigger (e.g., "Daily at 9:00 AM").
3.  Set the Action to **Start a Program**.
4.  In the Program/Script field, enter: `python` (or the absolute path to `.venv\Scripts\python.exe`).
5.  In the Add arguments field, enter: `scraper.py`
6.  In the Start in field, enter the directory path: `C:\Users\Jaymi\source\repos\price-monitor`

### GitHub Actions (Cloud)
To run the scraper daily on GitHub's servers for free, push this repository to GitHub and create `.github/workflows/monitor.yml`:
```yaml
name: Scheduled Phone Price Monitor

on:
  schedule:
    - cron: '0 9 * * *'  # Runs automatically every day at 9:00 AM UTC
  workflow_dispatch:     # Allows you to trigger it manually from GitHub Actions UI

jobs:
  check-price:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run Scraper
        env:
          SMTP_SERVER: ${{ secrets.SMTP_SERVER }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SENDER_EMAIL: ${{ secrets.SENDER_EMAIL }}
          SENDER_PASSWORD: ${{ secrets.SENDER_PASSWORD }}
          RECEIVER_EMAIL: ${{ secrets.RECEIVER_EMAIL }}
        run: python scraper.py
```
*(Add your environment variables as Repository Secrets in your GitHub repo settings under Settings > Secrets > Actions)*
