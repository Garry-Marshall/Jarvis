<div align="center"> 
<h1></h1>🤖 Discord AI Bot with LMStudio Integration</div></h1><br>
<br>
A powerful, modular Discord bot with local AI integration via LMStudio, featuring web search, file processing, text-to-speech, and comprehensive server configuration.<br>
Features • Quick Start • Commands • Configuration • Development<br>
</div> 
<hr>
✨ Features<br>

🧠 AI Capabilities<br>
•	✅ Local LLM Integration via LMStudio API<br>
•	✅ Model Selection - Switch between loaded models per server<br>
•	✅ Context-Aware Conversations - Maintains conversation history<br>
•	✅ Reasoning Model Support - Handles <think> tags automatically<br>
🔍 Enhanced Input Processing<br>
•	✅ Web Search - Automatic DuckDuckGo search when needed<br>
•	✅ URL Content Fetching - Extracts text from provided URLs<br>
•	✅ Image Processing - Vision model support for images<br>
•	✅ PDF Processing - Extracts and reads PDF content<br>
•	✅ Text File Support - Reads code files, documents, etc.<br>
🎙️ Voice & TTS<br>
•	✅ Voice Channel Integration - Bot joins and speaks in voice channels<br>
•	✅ Multiple Voices - 6 OpenAI-compatible voices (AllTalk TTS)<br>
•	✅ Auto-Disconnect - Leaves when alone in voice channel<br>
⚙️ Server Configuration<br>
•	✅ Custom System Prompts - Per-server AI personality<br>
•	✅ Temperature Control - Adjust response creativity<br>
•	✅ Token Limits - Control response length<br>
•	✅ Debug Logging - Per-server debug modes<br>
•	✅ Web Search Toggle - Enable/disable per server<br>
📊 Statistics & Management<br>
•	✅ Conversation Stats - Track tokens, response times, messages<br>
•	✅ History Management - Clear, reset, or view conversation history<br>
•	✅ Persistent Storage - Stats and settings saved across restarts<br>
<hr>
📁 Project Structure<br>
discord_bot/<br>
│<br>
├── 📄 bot.py                  # Main entry point<br>
├── 📄 requirements.txt        # Python dependencies<br>
├── 📄 .env                    # Configuration<br>
│<br>
├── 📁 config/                 # Settings and constants<br>
│   ├── settings.py<br>
│   ├── constants.py<br>
│   └── __init__.py<br>
│<br>
├── 📁 utils/                  # Helper functions<br>
│   ├── logging_config.py<br>
│   ├── text_utils.py<br>
│   ├── stats_manager.py<br>
│   ├── guild_settings.py<br>
│   └── __init__.py<br>
│<br>
├── 📁 services/               # Business logic<br>
│   ├── lmstudio.py           # LMStudio API integration<br>
│   ├── tts.py                # Text-to-speech<br>
│   ├── search.py             # Web search<br>
│   ├── content_fetch.py      # URL content fetching<br>
│   ├── file_processor.py     # File processing<br>
│   └── __init__.py<br>
│<br>
├── 📁 commands/               # Slash commands<br>
│   ├── conversation.py       # /reset, /history<br>
│   ├── stats.py              # /stats commands<br>
│   ├── voice.py              # /join, /leave, /voice<br>
│   ├── model.py              # /model selection<br>
│   ├── config_cmd.py         # /config command<br>
│   ├── help.py               # /help command<br>
│   └── __init__.py<br>
│<br>
└── 📁 core/                   # Bot core<br>
    ├── bot_instance.py       # Bot setup<br>
    ├── events.py             # Event handlers<br>
    └── __init__.py<br>
<br>
<hr>
🚀 Quick Start<br>
Prerequisites<br>
Requirement	Version	Link<br>
Python	3.8+	Download<br>
<br>
Discord Bot	Token Required	Create Bot<br>
<br>
LMStudio	Latest	Download<br>
<br>
AllTalk TTS	Optional	Download<br>
<br>
Installation<br>
<details> <summary><b>📥 Step 1: Clone Repository</b></summary> <br>
# Clone or download the repository<br>
git clone https://github.com/Garry-Marshall/Jarvis<br>
cd Jarvis<br>
<br>
# Create virtual environment (recommended)<br>
python -m venv venv<br>
<br>
# Activate virtual environment<br>
# On Linux/Mac:<br>
source venv/bin/activate<br>
# On Windows:<br>
venv\Scripts\activate<br>
</details> <details> <summary><b>📦 Step 2: Install Dependencies</b></summary> <br>
pip install -r requirements.txt<br>
</details> <details> <summary><b>⚙️ Step 3: Configure Bot</b></summary> <br>
Create a .env file in the project root:<br>
# REQUIRED: Your Discord bot token<br>
DISCORD_BOT_TOKEN=your-bot-token-here<br>
<br>
# REQUIRED: Comma-separated channel IDs where bot should respond<br>
DISCORD_CHANNEL_IDS=123456789012345678,987654321098765432<br>
<br>
# LMStudio API (default: localhost)<br>
LMSTUDIO_URL=http://localhost:1234/v1/chat/completions<br>
<br>
# Conversation settings<br>
MAX_HISTORY_MESSAGES=10<br>
CONTEXT_MESSAGES=5<br>
<br>
# Bot behavior<br>
IGNORE_BOTS=true<br>
ALLOW_DMS=true<br>
<br>
# File processing<br>
ALLOW_IMAGES=true<br>
MAX_IMAGE_SIZE=5<br>
ALLOW_TEXT_FILES=true<br>
MAX_TEXT_FILE_SIZE=2<br>
ALLOW_PDF=true<br>
MAX_PDF_SIZE=10<br>
<br>
# Model settings<br>
HIDE_THINKING=true<br>
<br>
# Voice/TTS settings<br>
ENABLE_TTS=true<br>
ALLTALK_URL=http://127.0.0.1:7851<br>
ALLTALK_VOICE=alloy<br>
</details> <details> <summary><b>🔑 Step 4: Get Channel IDs</b></summary> <br>
1.	Enable Developer Mode in Discord <br>
o	Settings → Advanced → Developer Mode ✅<br>
2.	Right-click a channel → Copy ID<br>
3.	Add to DISCORD_CHANNEL_IDS in .env <br>
o	Multiple channels: comma-separated<br>
</details> <details> <summary><b>▶️ Step 5: Run the Bot</b></summary> <br>
python bot.py<br>
Expected output:<br>
2024-01-13 10:00:00 [INFO] Bot has connected to Discord!<br>
2024-01-13 10:00:00 [INFO] Loaded LM Studio model(s): ['llama-2-7b']<br>
2024-01-13 10:00:00 [INFO] Synced 10 slash command(s)<br>
✅ Success! Your bot is now online.<br>
</details> <br>
<hr>
📖 Usage<br>
💬 Basic Conversation<br>
<table> <tr> <td width="30%"><b>Action</b></td> <td width="70%"><b>Example</b></td> </tr> <tr> <td>Simple message</td> <td> 
User: What is the weather like today?<br>
Bot: 🤔 Thinking...<br>
Bot: [Searches web and responds with weather info]<br>
</td> </tr> <tr> <td>With image</td> <td> 
User: [uploads sunset.jpg] What's in this image?<br>
Bot: I can see a beautiful sunset over the ocean with <br>
     vibrant orange and pink colors reflecting on the water...<br>
</td> </tr> <tr> <td>With PDF/Files</td> <td> 
User: [uploads report.pdf] Summarize this document<br>
Bot: This document discusses quarterly sales performance,<br>
     highlighting a 23% increase in revenue...<br>
</td> </tr> </table> 
🎮 Slash Commands<br>
🗨️ Conversation Management<br>
Command	Description	Usage<br>
/reset	Clear conversation history	/reset<br>
/history	Show conversation length	/history<br>
/stats	Display detailed statistics	/stats<br>
/stats_reset	Reset statistics	/stats_reset<br>
⚙️ Configuration<br>
Note: Commands marked with 🔒 require Administrator permissions<br>
Command	Description	Example<br>
/config show show	View all settings	/config show show<br>
/config system set 🔒	Set custom system prompt	/config system set You are a helpful coding assistant<br>
/config system show	View current system prompt	/config system show<br>
/config system clear 🔒	Reset to default prompt	/config system clear<br>
/config temperature set 🔒	Adjust creativity (0.0-2.0)	/config temperature set 0.8<br>
/config temperature show	View current temperature	/config temperature show<br>
/config max_tokens set 🔒	Limit response length	/config max_tokens set 2000<br>
/config max_tokens show	View current limit	/config max_tokens show<br>
/config debug on/off 🔒	Toggle debug logging	/config debug on<br>
/config search on/off 🔒	Toggle web search	/config search off<br>
/config clear last	Remove last interaction	/config clear last<br>
🧠 Model & Voice<br>
Command	Description<br>
/model	Select AI model from dropdown menu<br>
/voice	Choose TTS voice (alloy, echo, fable, nova, onyx, shimmer)<br>
/join	Join your current voice channel<br>
/leave	Leave voice channel<br>
❓ Help<br>
Command	Description<br>
/help	Show all commands and usage instructions<br>
<hr>
🔧 Advanced Configuration<br>
<details> <summary><b>🧠 Custom System Prompts</b></summary> <br>
Set a unique personality per server:<br>
/config system set You are a helpful coding assistant specializing in Python and JavaScript. Always provide code examples and explain your reasoning.<br>
Examples:<br>
•	Customer Support: You are a friendly customer support agent. Be empathetic and solution-focused.<br>
•	Tutor: You are an experienced teacher. Explain concepts clearly with examples and analogies.<br>
•	Creative Writer: You are a creative writing assistant. Help with storytelling, character development, and plot ideas.<br>
</details> <details> <summary><b>🌡️ Temperature Settings</b></summary> <br>
Control response creativity and randomness:<br>
Temperature	Behavior	Best For<br>
0.0 - 0.3	Focused, deterministic	Code, facts, technical content<br>
0.4 - 0.7	Balanced (default: 0.7)	General conversation<br>
0.8 - 1.2	Creative, varied	Brainstorming, creative writing<br>
1.3 - 2.0	Highly creative, unpredictable	Experimental, artistic content<br>
/config temperature set 0.8<br>
</details> <details> <summary><b>📝 Token Limits</b></summary> <br>
Control maximum response length:<br>
# Limit to 2000 tokens<br>
/config max_tokens set 2000<br>
<br>
# Unlimited tokens<br>
/config max_tokens set -1<br>
<br>
# View current setting<br>
/config max_tokens show<br>
Note: Actual output length may be shorter depending on model and prompt.<br>
</details> <details> <summary><b>🐞 Debug Logging</b></summary> <br>
Enable detailed logging for troubleshooting:<br>
# Enable debug mode<br>
/config debug on<br>
<br>
# Set log level<br>
/config debug level debug  # Verbose<br>
/config debug level info   # Standard<br>
<br>
# View current settings<br>
/config debug show<br>
Logs are saved to: Logs/bot_YYYY-MM-DD.log<br>
Debug info includes:<br><br>
•	Full API messages (with thinking tags)<br>
•	Token counts and timing<br>
•	Search context details<br>
•	Error stack traces<br>
</details> <details> <summary><b>🔍 Web Search Control</b></summary> <br>
Toggle automatic web search per server:<br>
# Disable web search<br>
/config search off<br>
<br>
# Enable web search<br>
/config search on<br>
<br>
# Check status<br>
/config search show<br>
Search Triggers: The bot automatically searches when messages contain phrases like:<br>
•	"search for..."<br>
•	"what's the latest..."<br>
•	"current news about..."<br>
•	"weather in..."<br>
</details> <br>
<hr>
🛠️ Development<br>
Project Architecture<br>
graph TD
    A[bot.py - Entry Point] --> B[core/events.py]
    B --> C[commands/]
    B --> D[services/]
    D --> E[LMStudio API]
    D --> F[Web Search]
    D --> G[TTS Service]
    C --> H[utils/]
    D --> H
    H --> I[Stats Manager]
    H --> J[Guild Settings]
<details> <summary><b>📦 Package Details</b></summary> <br>
Package	Purpose	Key Files<br>
config/	Configuration management	settings.py, constants.py<br>
utils/	Helper functions	text_utils.py, stats_manager.py, guild_settings.py<br>
services/	Business logic	lmstudio.py, tts.py, search.py, file_processor.py<br>
commands/	Slash commands	All command handlers<br>
core/	Bot core	bot_instance.py, events.py<br>
</details> <br>
<br>
🐛 Troubleshooting<br>
<details> <summary><b>Bot doesn't respond to messages</b></summary> <br>
Possible causes:<br>
1.	Wrong channel IDs<br>
2.	# Check your .env file<br>
3.	DISCORD_CHANNEL_IDS=123456789012345678<br>
4.	<br>
5.	# Verify in logs:<br>
6.	# Should see: "Listening in X channel(s)"<br>
7.	Missing permissions<br>
o	Bot needs: Read Messages, Send Messages, Embed Links, Attach Files<br>
o	Check in Server Settings → Roles → Your Bot Role<br>
8.	Bot not in channel<br>
o	Ensure bot was invited with correct permissions<br>
o	Re-invite with this URL (replace CLIENT_ID):<br>
9.	https://discord.com/api/oauth2/authorize?client_id=CLIENT_ID&permissions=412317273088&scope=bot%20applications.commands<br>
</details> <details> <summary><b>"No models found in LMStudio"</b></summary> <br>
Solution:<br>
1.	Open LMStudio application<br>
2.	Navigate to "Models" tab<br>
3.	Click "Load Model" for your desired model<br>
4.	Wait for model to fully load (status bar shows 100%)<br>
5.	Restart the Discord bot<br>
Verify:<br>
# You should see in logs:<br>
[INFO] Loaded LM Studio model(s): ['your-model-name']<br>
</details> <details> <summary><b>Import errors / Module not found</b></summary> <br>
Cause: Running from wrong directory or missing __init__.py files<br>
Solution:<br>
# Always run from project root<br>
cd Jarvis<br>
python bot.py<br>
<br>
# NOT from subdirectories:<br>
# ❌ cd Jarvis/core && python ../bot.py<br>
<br>
# Ensure all __init__.py files exist:<br>
touch config/__init__.py<br>
touch utils/__init__.py<br>
touch services/__init__.py<br>
touch commands/__init__.py<br>
touch core/__init__.py<br>
</details> <details> <summary><b>Slash commands not appearing</b></summary> <br>
Solution:<br>
1.	Wait 1 hour - Discord caches slash commands globally<br>
2.	Refresh Discord – Press CTRL-D in Discord.<br>
3.	Check logs for sync errors: <br>
4.	[INFO] Synced 10 slash command(s)<br>
5.	Test in DM - Slash commands appear faster in DMs<br>
</details> <details> <summary><b>Permission errors</b></summary> <br>
Required bot permissions:<br>
Permission	Why Needed<br>
View Channels	See messages<br>
Send Messages	Respond to users<br>
Embed Links	Rich formatting<br>
Attach Files	Send images/files<br>
Read Message History	Load context<br>
Use Slash Commands	Execute commands<br>
Connect	Join voice (optional)<br>
Speak	TTS playback (optional)<br>
Bot invite URL template:<br>
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=412317273088&scope=bot%20applications.commands<br>
</details> <details> <summary><b>Voice/TTS not working</b></summary> <br>
Checklist:<br>
•	[ ] ENABLE_TTS=true in .env<br>
•	[ ] AllTalk TTS running at ALLTALK_URL<br>
•	[ ] Bot is in voice channel (/join)<br>
•	[ ] Bot has Connect and Speak permissions<br>
•	[ ] FFmpeg installed (required for audio playback)<br>
Install FFmpeg:<br>
# Ubuntu/Debian<br>
sudo apt-get install ffmpeg<br>
<br>
# macOS<br>
brew install ffmpeg<br>
<br>
# Windows<br>
# Download from: https://ffmpeg.org/download.html<br>
<br>
<hr>
📊 Statistics Files<br>
The bot automatically creates and maintains these files:<br>
File	Purpose	Can Delete?<br>
channel_stats.json	Conversation statistics (tokens, times, messages)	✅ Yes - Will recreate with defaults<br>
guild_settings.json	Server configurations (prompts, temperature, etc.)	⚠️ Caution - Settings will be lost<br>
Logs/bot_*.log	Daily log files	✅ Yes - Old logs can be deleted<br>
Example stats structure:<br>
{<br>
  "123456789": {<br>
    "total_messages": 42,<br>
    "prompt_tokens_estimate": 15230,<br>
    "response_tokens_cleaned": 8450,<br>
    "average_response_time": 2.3<br>
  }<br>
}<br>
<hr>
🔒 Security Best Practices<br>
⚠️ IMPORTANT: Follow these security guidelines<br>
Environment Variables<br>
•	✅ DO: Keep .env file in .gitignore<br>
•	✅ DO: Use separate tokens for dev/production<br>
•	❌ DON'T: Commit .env to version control<br>
•	❌ DON'T: Share your bot token publicly<br>
Token Exposed?<br>
If your bot token is accidentally exposed:<br>
1.	Immediately regenerate in Discord Developer Portal<br>
2.	Update .env with new token<br>
3.	Restart bot<br>
4.	Review bot's recent activity<br>
Permissions<br>
•	Principle of least privilege: Only grant permissions the bot actually needs<br>
•	Review regularly: Audit bot permissions in all servers<br>
•	Test in dev server first: Before adding new features<br>
Rate Limiting<br>
The bot includes built-in rate limiting for:<br>
•	Web searches (10s cooldown per server)<br>
•	API requests (handled by discord.py)<br>
<hr>
🤝 Contributing<br>
We welcome contributions! Here's how to help:<br>
Reporting Issues<br>
<details> <summary><b>🐛 Bug Reports</b></summary> <br>
Please include:<br>
•	Bot version or commit hash<br>
•	Python version: python --version<br>
•	OS: Windows/Mac/Linux<br>
•	Error logs from Logs/ directory<br>
•	Steps to reproduce<br>
</details> <details> <summary><b>💡 Feature Requests</b></summary> <br>
Describe:<br>
•	Use case: What problem does this solve?<br>
•	Proposed solution: How should it work?<br>
•	Alternatives considered: Other approaches?<br>
</details> <br>
Development Workflow<br>
1.	Fork the repository<br>
2.	Create a branch: git checkout -b feature/amazing-feature<br>
3.	Make changes with clear, focused commits<br>
4.	Test thoroughly in a dev server<br>
5.	Update docs if needed (README, docstrings)<br>
6.	Submit PR with description of changes<br>
Code Guidelines<br>
•	Follow existing code style<br>
•	Add docstrings to new functions<br>
•	Update README.md for user-facing changes<br>
•	Keep commits atomic and well-described<br>
<hr>
📝 License<br>
This project is licensed under the MIT License - see the LICENSE file for details.<br>
TL;DR: You can use, modify, and distribute this code freely, just keep the copyright notice.<br>
<hr>
🙏 Acknowledgments<br>
This project is built on these amazing open-source projects:<br>
<table> <tr> <td align="center" width="25%"> <a href="https://github.com/Rapptz/discord.py"> <img src="https://raw.githubusercontent.com/Rapptz/discord.py/master/docs/_static/discord_py_logo.png" width="60px" alt="discord.py"/><br/> <b>discord.py</b> </a><br/> Discord API wrapper </td> <td align="center" width="25%"> <a href="https://lmstudio.ai/"> <b>🖥️ LMStudio</b> </a><br/> Local LLM runtime </td> <td align="center" width="25%"> <a href="https://github.com/deedy5/ddgs"> <b>🦆 DuckDuckGo</b> </a><br/> Privacy-first search </td> <td align="center" width="25%"> <a href="https://github.com/adbar/trafilatura"> <b>📄 Trafilatura</b> </a><br/> Web scraping </td> </tr> </table> 
Special thanks to:<br>
•	AllTalk TTS for OpenAI-compatible text-to-speech<br>
•	The Discord.py community for excellent documentation<br>
•	All contributors and users of this project<br>
<hr>
📧 Support & Community<br>
<div align="center"> 
   
</div> 
•	🐛 Bug Reports: GitHub Issues<br>
•	💬 Questions: GitHub Discussions<br>
•	📖 Wiki: Documentation<br>
<hr>
<div align="center"> 
⭐ Star this repo if you find it useful! ⭐<br>
Made with ❤️ by the community<br>
⬆ Back to Top<br>
</div>

