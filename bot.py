import discord
import datetime
import asyncio
import os
import re
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.messages = True
intents.reactions = True
intents.guilds = True
intents.message_content = True
intents.members = True 

client = discord.Client(intents=intents)

ATTENDANCE_TIME = "00:13"
SUMMARY_TIME = "00:14"
attendance_messages = {}

async def send_daily_messages():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    if channel is None:
        print(f"ERROR: Cannot find channel with ID {CHANNEL_ID}. Check permissions.")
        return

    while True:
        now = datetime.datetime.now().strftime("%H:%M")

        if now == ATTENDANCE_TIME:
            today = str(datetime.date.today())
            message = await channel.send(f"Attendance for {today}\nReact with ✅ for Present, ❌ for Absent.")
            await message.add_reaction("✅")
            await message.add_reaction("❌")
            attendance_messages[today] = message.id
            print(f"📢 Attendance message sent at {now}")

        if now == SUMMARY_TIME:
            await send_summary(channel)

        await asyncio.sleep(60)

async def fetch_attendance(message_id):
    if not message_id:
        return {}, {}

    channel = client.get_channel(CHANNEL_ID)
    message = await channel.fetch_message(message_id)
    present_users = {}
    absent_users = {}

    for reaction in message.reactions:
        if reaction.emoji == "✅":
            async for user in reaction.users():
                if not user.bot:
                    present_users[user.id] = user.mention
        elif reaction.emoji == "❌":
            async for user in reaction.users():
                if not user.bot:
                    absent_users[user.id] = user.mention

    # Fetch all members and mark those who didn't react as absent
    guild = channel.guild
    all_members = {member.id: member.mention for member in guild.members if not member.bot}

    for member_id, mention in all_members.items():
        if member_id not in present_users and member_id not in absent_users:
            absent_users[member_id] = mention

    return present_users, absent_users

async def send_summary(channel):
    today = str(datetime.date.today())

    if today in attendance_messages:
        present_users, absent_users = await fetch_attendance(attendance_messages[today])

        embed = discord.Embed(title=f"Attendance Summary for {today}", color=discord.Color.blue())
        embed.add_field(name=f"Present ({len(present_users)})", value="\n".join(present_users.values()) if present_users else "None", inline=False)
        embed.add_field(name=f"Absent ({len(absent_users)})", value="\n".join(absent_users.values()) if absent_users else "None", inline=False)
        embed.set_footer(text="whatever")

        await channel.send(embed=embed)

@client.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("!attendance"):
        match = re.match(r"!attendance\s+<@!?(\d+)>\s+(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})?", message.content)
        
        if not match:
            await message.channel.send("Usage: `!attendance @user dd/mm/yyyy - dd/mm/yyyy`")
            return

        user_id = int(match.group(1))
        start_date = match.group(2)
        end_date = match.group(3) if match.group(3) else start_date

        start_dt = datetime.datetime.strptime(start_date, "%d/%m/%Y").date()
        end_dt = datetime.datetime.strptime(end_date, "%d/%m/%Y").date()

        if user_id not in [m.id for m in message.mentions]:
            await message.channel.send("Please mention a valid user.")
            return

        user_mention = f"<@{user_id}>"
        attendance_results = []

        for day, msg_id in attendance_messages.items():
            day_dt = datetime.datetime.strptime(day, "%Y-%m-%d").date()
            if start_dt <= day_dt <= end_dt:
                present_users, absent_users = await fetch_attendance(msg_id)
                if user_id in present_users:
                    attendance_results.append(f"{day}: ✅ Present")
                else:
                    attendance_results.append(f"{day}: ❌ Absent")

        if attendance_results:
            response = f"📅 Attendance record for {user_mention}:\n" + "\n".join(attendance_results)
        else:
            response = f"No attendance records found for {user_mention} in the given date range."

        await message.channel.send(response)

@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")
    client.loop.create_task(send_daily_messages())

client.run(TOKEN)