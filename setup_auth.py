#!/usr/bin/env python3
"""
One-time Telegram authentication setup for autoforward bot
Run this locally before deploying to Vercel
"""

import os
import asyncio
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def setup_authentication():
    """Setup Telegram authentication and create session file"""
    print("🔑 Telegram Autoforward Bot - Authentication Setup")
    print("=" * 50)
    
    # Get API credentials
    api_id = input("Enter your API ID (from https://my.telegram.org/apps): ").strip()
    api_hash = input("Enter your API Hash: ").strip()
    phone = input("Enter your phone number (with country code, e.g., +1234567890): ").strip()
    
    if not all([api_id, api_hash, phone]):
        print("❌ All fields are required!")
        return False
    
    try:
        api_id = int(api_id)
    except ValueError:
        print("❌ API ID must be a number!")
        return False
    
    print(f"\n📱 Connecting to Telegram with phone: {phone}")
    
    # Create client
    client = TelegramClient('telegram_session', api_id, api_hash)
    
    try:
        await client.start(phone=phone)
        
        if await client.is_user_authorized():
            print("✅ Successfully authenticated!")
            
            # Get user info
            me = await client.get_me()
            print(f"👤 Logged in as: {me.first_name} {me.last_name or ''} (@{me.username})")
            
            # Create .env file with settings
            env_content = f"""# Telegram API Credentials
TELEGRAM_API_ID={api_id}
TELEGRAM_API_HASH={api_hash}
TELEGRAM_PHONE={phone}

# Forwarding Configuration (update these)
SOURCE_CHAT=@source_channel_username
DESTINATION_CHAT=@destination_channel_username

# Optional Configuration
KEYWORDS=keyword1,keyword2,keyword3
FORWARD_MEDIA=true
DELAY_SECONDS=2

# Database URL (set this in Vercel)
DATABASE_URL=your_postgresql_database_url

# Security
SECRET_KEY=your_random_secret_key_here
"""
            
            with open('.env', 'w') as f:
                f.write(env_content)
            
            print("\n📄 Created .env file with your configuration")
            print("\n🚀 Next steps:")
            print("1. Update SOURCE_CHAT and DESTINATION_CHAT in .env file")
            print("2. Upload telegram_session.session file to your project")
            print("3. Set environment variables in Vercel dashboard")
            print("4. Deploy to Vercel")
            print("\n✨ Your bot is ready for 24/7 deployment!")
            
            return True
            
        else:
            print("❌ Authentication failed")
            return False
            
    except SessionPasswordNeededError:
        print("❌ Two-factor authentication is enabled.")
        print("Please disable 2FA temporarily or handle it manually.")
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
        
    finally:
        await client.disconnect()

if __name__ == '__main__':
    print("🤖 Telegram Autoforward Bot - Setup")
    print("This script will authenticate your account and create session files.")
    print("Run this ONCE before deploying to Vercel.\n")
    
    result = asyncio.run(setup_authentication())
    
    if result:
        print("\n🎉 Setup completed successfully!")
    else:
        print("\n💔 Setup failed. Please try again.")
