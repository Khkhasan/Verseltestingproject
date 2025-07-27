# Telegram Autoforward Bot - Vercel Deployment Guide

This guide will help you deploy a 24/7 Telegram autoforward bot to Vercel that automatically forwards messages between chats without manual intervention.

## 🚀 Quick Setup

### Step 1: Initial Authentication (One-time setup)

Before deploying to Vercel, you need to authenticate your Telegram account locally:

```bash
# Install dependencies
pip install telethon python-dotenv

# Run the authentication setup
python setup_auth.py
```

This script will:
1. Ask for your Telegram API credentials
2. Send a verification code to your phone
3. Create a session file (`telegram_session.session`)
4. Generate environment variables template

### Step 2: Get Telegram API Credentials

1. Go to https://my.telegram.org/apps
2. Log in with your phone number
3. Create a new application
4. Note down your `api_id` and `api_hash`

### Step 3: Configure Environment Variables

Set these in your Vercel dashboard (Settings → Environment Variables):

```env
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+1234567890
SOURCE_CHAT=@source_channel_username
DESTINATION_CHAT=@destination_channel_username
KEYWORDS=keyword1,keyword2,keyword3
FORWARD_MEDIA=true
DELAY_SECONDS=2
SECRET_KEY=your_random_secret_key
```

### Step 4: Deploy to Vercel

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

## 📁 Project Structure

```
├── api/
│   └── index.py          # Main bot application
├── templates/
│   └── dashboard.html    # Web dashboard
├── setup_auth.py         # One-time authentication script
├── vercel.json          # Vercel configuration
├── telegram_session.session  # Session file (created by setup)
└── README_DEPLOYMENT.md
```

## 🔧 Configuration Options

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_API_ID` | API ID from my.telegram.org | `12345678` |
| `TELEGRAM_API_HASH` | API Hash from my.telegram.org | `abcdef1234567890` |
| `TELEGRAM_PHONE` | Your phone number | `+1234567890` |
| `SOURCE_CHAT` | Chat to monitor | `@deals_channel` |
| `DESTINATION_CHAT` | Where to forward | `@my_channel` |
| `KEYWORDS` | Filter keywords (optional) | `deal,discount,sale` |
| `FORWARD_MEDIA` | Forward images/files | `true` or `false` |
| `DELAY_SECONDS` | Delay between forwards | `2` |

## 🎯 Features

- **24/7 Operation**: Runs continuously on Vercel
- **Auto-Start**: Automatically starts when deployed
- **Web Dashboard**: Monitor status and statistics
- **Keyword Filtering**: Only forward messages with specific keywords
- **Media Support**: Forward images, videos, and files
- **Rate Limiting**: Built-in delays to avoid Telegram limits
- **Error Handling**: Comprehensive error logging and recovery

## 📊 Web Dashboard

Access your dashboard at: `https://your-app.vercel.app`

Features:
- Real-time bot status
- Message statistics
- Configuration display
- Start/stop controls
- Error logs

## 🔒 Security Notes

1. **Keep your session file secure** - it contains authentication data
2. **Use strong SECRET_KEY** for Flask sessions
3. **Don't share your API credentials**
4. **Monitor the error logs** for any issues

## 🐛 Troubleshooting

### Bot not starting
- Check all environment variables are set
- Verify session file exists in project root
- Check Vercel function logs

### Authentication errors
- Re-run `setup_auth.py` to refresh session
- Ensure phone number format includes country code
- Check if 2FA is enabled (may require additional setup)

### Messages not forwarding
- Verify SOURCE_CHAT and DESTINATION_CHAT are accessible
- Check if bot has permission to read from source
- Ensure destination chat allows the bot to send messages

### Rate limiting
- Increase DELAY_SECONDS value
- Reduce message frequency if possible
- Monitor for FloodWaitError in logs

## 📱 Chat ID vs Username

You can use either format for SOURCE_CHAT and DESTINATION_CHAT:

- **Username**: `@channel_username` or `@username`
- **Chat ID**: `-1001234567890` (for channels/groups)

To get chat ID:
1. Add @userinfobot to your group/channel
2. Send `/id` command
3. Use the returned ID

## 🔄 Auto-Recovery

The bot includes automatic recovery features:
- Reconnects on network issues
- Retries failed forwards
- Logs errors for debugging
- Maintains statistics across restarts

## 📈 Monitoring

Monitor your bot through:
- Web dashboard statistics
- Vercel function logs
- Telegram bot status messages
- Error count in dashboard

## 🆘 Support

If you encounter issues:
1. Check the web dashboard for errors
2. Review Vercel function logs
3. Ensure all environment variables are correct
4. Re-run authentication setup if needed

---

**Note**: This bot is based on Khkhasan's Telegram autoforward script, optimized for 24/7 Vercel deployment with automated authentication and web dashboard monitoring.
