# 📦 Austrian Post Tracking Bot

A simple Discord bot for tracking Austrian Post shipments directly from Discord.

Uses Playwright to fetch the current shipment information from the Austrian Post tracking page and returns it as a Discord embed.

No database. No unnecessary backend. Just Discord → Post tracking → useful result.

## Features

* `/track <sendungsnummer>` — Track an Austrian Post shipment
* `/post <sendungsnummer>` — Alias for `/track`
* Shipment status and tracking history
* Delivery date/time
* Destination ZIP code
* Weight and dimensions
* Status-based embed colors
* Input validation
* Headless Chromium via Playwright
* `.env` configuration

## Preview

![Tracking result](https://raw.githubusercontent.com/DXXNS/PAT-Scraper-Bot/refs/heads/master/img/post.png?token=GHSAT0AAAAAAEHLD6FZME2JIK3LUDPLJC6Y2VMYM6Q)

Both `/track` and `/post` use the same tracking logic and produce the same result.

## Stack

* **Python**
* **discord.py**
* **Discord Slash Commands**
* **Playwright**
* **Chromium**
* **python-dotenv**
* **Regex-based parsing**

## Project Structure

```text
.
├── bot.py
├── .env
├── .gitignore
├── requirements.txt
└── assets/
    └── track.png
```

## Requirements

* Python 3.10+
* Discord Bot
* Discord Application
* Playwright
* Chromium

## Installation

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

python -m venv .venv
```

### Windows

```powershell
.venv\Scripts\activate
```

### Linux

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
playwright install chromium
```

On Linux:

```bash
playwright install-deps chromium
```

## Configuration

Create a `.env` file:

```env
DISCORD_TOKEN=your_discord_bot_token
```

The bot loads the token from the environment and exits if it isn't configured.

Add `.env` to `.gitignore`:

```gitignore
.env
.venv/
__pycache__/
*.pyc
```

## Usage

Start the bot:

```bash
python bot.py
```

The bot automatically synchronizes its slash commands when it starts.

### Track a shipment

```text
/track sendungsnummer:123456789012
```

### Alternative command

```text
/post sendungsnummer:123456789012
```

`/post` is just an alias for `/track`; both commands execute the same tracking function.

## Returned Data

Depending on what Austrian Post provides, the bot extracts:

* Sendungsnummer
* Status
* Delivery date/time
* Destination ZIP code
* Weight
* Dimensions
* Latest event
* Shipment history

## How It Works

```text
Discord
   │
   │ /track or /post
   ▼
Discord Bot
   │
   ▼
Playwright + Chromium
   │
   ▼
Österreichische Post
   │
   ▼
Tracking Page
   │
   ▼
Text / Regex Parsing
   │
   ▼
Discord Embed
```

The bot opens the Austrian Post tracking page with a headless Chromium instance, reads the rendered page text and extracts the relevant tracking information.

## Status Colors

```text
ZUGESTELLT   → Green
ZUSTELLUNG   → Orange
VERTEILUNG   → Blue
RETOURE      → Red
Other        → Light Grey
```

## Error Handling

Invalid tracking numbers are rejected before making a request.

The bot also handles failed tracking requests and returns an error message if the Post page cannot be reached.

## Dependencies

```txt
discord.py
python-dotenv
playwright
```

## Notes

This project uses the public Austrian Post tracking page rather than an official Post API.

Because the page is parsed directly, changes to the Austrian Post website can break the tracking parser.

Current tracking URL:

```text
https://www.post.at/s/sendungssuche?snr={tracking_number}
```

## Disclaimer

This project is unofficial and is not affiliated with or endorsed by Österreichische Post AG.

## License

MIT
