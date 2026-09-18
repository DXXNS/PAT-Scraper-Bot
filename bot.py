import os
import re
import asyncio

import discord
from discord import app_commands
from dotenv import load_dotenv
from playwright.async_api import async_playwright


# ============================================================
# KONFIGURATION
# ============================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    raise RuntimeError(
        "DISCORD_TOKEN wurde nicht gefunden. "
        "Bitte deine .env Datei überprüfen."
    )

POST_URL = "https://www.post.at/s/sendungssuche?snr={}"


# ============================================================
# DISCORD BOT
# ============================================================

intents = discord.Intents.default()

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


# ============================================================
# POST TRACKING
# ============================================================

async def lookup_post(tracking_number: str):

    url = POST_URL.format(tracking_number)

    async with async_playwright() as p:

        browser = await p.chromium.launch(
            headless=True
        )

        context = await browser.new_context(
            locale="de-AT",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            )
        )

        page = await context.new_page()

        try:

            await page.goto(
                url,
                wait_until="networkidle",
                timeout=60000
            )

            await page.wait_for_timeout(2000)

            text = await page.locator("body").inner_text()

            # ------------------------------------------------
            # SENDUNGSNUMMER
            # ------------------------------------------------

            number_match = re.search(
                r"SENDUNGSNUMMER\s*\n\s*(\d{10,30})",
                text,
                re.IGNORECASE
            )

            found_number = (
                number_match.group(1)
                if number_match
                else tracking_number
            )

            # ------------------------------------------------
            # STATUS
            # ------------------------------------------------

            status = "Unbekannt"

            statuses = [
                "ZUGESTELLT",
                "SENDUNG IN ZUSTELLUNG",
                "IN ZUSTELLUNG",
                "SENDUNG IN VERTEILUNG",
                "IN VERTEILUNG",
                "ABHOLBEREIT",
                "SENDUNG ANGENOMMEN",
                "IN BEARBEITUNG",
                "NICHT ZUGESTELLT",
                "RETOURE"
            ]

            for possible_status in statuses:

                if possible_status.lower() in text.lower():

                    status = possible_status
                    break

            # ------------------------------------------------
            # ZUGESTELLT
            # ------------------------------------------------

            delivered = None

            match = re.search(
                r"Zugestellt am\s+"
                r"([0-9]{1,2}\.[0-9]{1,2}\.[0-9]{4})"
                r"\s+"
                r"([0-9]{1,2}:[0-9]{2})",
                text,
                re.IGNORECASE
            )

            if match:

                delivered = (
                    f"{match.group(1)} "
                    f"{match.group(2)}"
                )

            # ------------------------------------------------
            # ZIEL-PLZ
            # ------------------------------------------------

            postal_code = None

            match = re.search(
                r"Ziel-Postleitzahl anzeigen\s*\n\s*(\d{4})",
                text,
                re.IGNORECASE
            )

            if match:
                postal_code = match.group(1)

            # ------------------------------------------------
            # GEWICHT
            # ------------------------------------------------

            weight = None

            match = re.search(
                r"Gewicht\s*\n\s*([0-9.,]+\s*kg)",
                text,
                re.IGNORECASE
            )

            if match:
                weight = match.group(1)

            # ------------------------------------------------
            # MASSE
            # ------------------------------------------------

            dimensions = None

            match = re.search(
                r"Maße\s*\n\s*"
                r"([0-9]+\s*L\s*x\s*"
                r"[0-9]+\s*B\s*x\s*"
                r"[0-9]+\s*H\s*cm)",
                text,
                re.IGNORECASE
            )

            if match:
                dimensions = match.group(1)

            # ------------------------------------------------
            # SENDUNGSVERLAUF
            # ------------------------------------------------

            history = []

            history_match = re.search(
                r"Sendungsverlauf\s*(.*?)(?:Feedback geben|Schadensmeldung)",
                text,
                re.IGNORECASE | re.DOTALL
            )

            if history_match:

                history_text = history_match.group(1)

                lines = [
                    line.strip()
                    for line in history_text.splitlines()
                    if line.strip()
                ]

                months = {
                    "JAN", "FEB", "MÄR",
                    "APR", "MAI", "JUN",
                    "JUL", "AUG", "SEP",
                    "OKT", "NOV", "DEZ"
                }

                current_event = []

                for line in lines:

                    if line.upper() in months:
                        continue

                    if re.fullmatch(r"\d{1,2}", line):
                        continue

                    if re.fullmatch(r"\d{1,2}:\d{2}", line):
                        continue

                    if re.fullmatch(r"PLZ\s+\d{4}", line):
                        continue

                    current_event.append(line)

                # Nur die ersten sinnvollen Ereignisse
                history = current_event[:12]

            # ------------------------------------------------
            # LETZTES EREIGNIS
            # ------------------------------------------------

            last_event = None

            if history:
                last_event = history[0]

            return {
                "number": found_number,
                "status": status,
                "delivered": delivered,
                "postal_code": postal_code,
                "weight": weight,
                "dimensions": dimensions,
                "last_event": last_event,
                "history": history,
                "url": url
            }

        finally:

            await browser.close()


# ============================================================
# STATUS FARBE
# ============================================================

def get_status_color(status):

    status_upper = status.upper()

    if "ZUGESTELLT" in status_upper:
        return discord.Color.green()

    if "ZUSTELLUNG" in status_upper:
        return discord.Color.orange()

    if "VERTEILUNG" in status_upper:
        return discord.Color.blue()

    if "RETOURE" in status_upper:
        return discord.Color.red()

    return discord.Color.light_grey()


# ============================================================
# /TRACK
# ============================================================

@tree.command(
    name="track",
    description="Österreichische Post Sendung verfolgen"
)
@app_commands.describe(
    sendungsnummer="Die Sendungsnummer der Österreichischen Post"
)
async def track(
    interaction: discord.Interaction,
    sendungsnummer: str
):

    # --------------------------------------------------------
    # Nummer bereinigen
    # --------------------------------------------------------

    sendungsnummer = re.sub(
        r"\s+",
        "",
        sendungsnummer
    )

    # --------------------------------------------------------
    # Validierung
    # --------------------------------------------------------

    if not sendungsnummer.isdigit():

        await interaction.response.send_message(
            "❌ Die Sendungsnummer darf nur Zahlen enthalten.",
            ephemeral=True
        )

        return

    if len(sendungsnummer) < 10:

        await interaction.response.send_message(
            "❌ Die Sendungsnummer ist zu kurz.",
            ephemeral=True
        )

        return

    # --------------------------------------------------------
    # Loading
    # --------------------------------------------------------

    await interaction.response.defer()

    try:

        data = await lookup_post(sendungsnummer)

    except Exception as e:

        print("Tracking-Fehler:", repr(e))

        await interaction.followup.send(
            "❌ Die Sendung konnte nicht abgerufen werden.\n"
            "Möglicherweise ist die Post-Seite gerade nicht erreichbar."
        )

        return

    # --------------------------------------------------------
    # EMBED
    # --------------------------------------------------------

    embed = discord.Embed(
        title="📦 Österreichische Post",
        url=data["url"],
        color=get_status_color(data["status"])
    )

    embed.add_field(
        name="📋 Sendungsnummer",
        value=f"`{data['number']}`",
        inline=False
    )

    embed.add_field(
        name="📊 Status",
        value=f"**{data['status']}**",
        inline=False
    )

    if data["delivered"]:

        embed.add_field(
            name="📅 Zugestellt",
            value=data["delivered"],
            inline=True
        )

    if data["postal_code"]:

        embed.add_field(
            name="📍 Ziel-PLZ",
            value=data["postal_code"],
            inline=True
        )

    if data["weight"]:

        embed.add_field(
            name="⚖️ Gewicht",
            value=data["weight"],
            inline=True
        )

    if data["dimensions"]:

        embed.add_field(
            name="📐 Maße",
            value=data["dimensions"],
            inline=True
        )

    if data["last_event"]:

        embed.add_field(
            name="🕐 Letztes Ereignis",
            value=data["last_event"],
            inline=False
        )

    # --------------------------------------------------------
    # VERLAUF
    # --------------------------------------------------------

    if data["history"]:

        history_text = "\n".join(
            f"• {item}"
            for item in data["history"][:8]
        )

        # Discord Embed Field max. 1024 Zeichen
        if len(history_text) > 1000:

            history_text = history_text[:997] + "..."

        embed.add_field(
            name="📜 Sendungsverlauf",
            value=history_text,
            inline=False
        )

    embed.set_footer(
        text="Österreichische Post • Tracking Lookup"
    )

    await interaction.followup.send(
        embed=embed
    )


# ============================================================
# /POST
# Alias für /track
# ============================================================

@tree.command(
    name="post",
    description="Österreichische Post Sendung nachschauen"
)
@app_commands.describe(
    sendungsnummer="Die Sendungsnummer"
)
async def post(
    interaction: discord.Interaction,
    sendungsnummer: str
):

    await track.callback(
        interaction,
        sendungsnummer
    )


# ============================================================
# BOT START
# ============================================================

@client.event
async def on_ready():

    print()
    print("==========================================")
    print("📦 Post Tracking Discord Bot")
    print("==========================================")
    print(f"🤖 Eingeloggt als: {client.user}")
    print(f"🆔 Bot-ID: {client.user.id}")
    print("==========================================")

    try:

        synced = await tree.sync()

        print(
            f"✅ {len(synced)} Slash Commands synchronisiert."
        )

    except Exception as e:

        print(
            "❌ Fehler beim Synchronisieren:",
            repr(e)
        )


# ============================================================
# START
# ============================================================

client.run(TOKEN)