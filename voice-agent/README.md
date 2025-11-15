# Simple Voice Bot with Pipecat

A simple voice bot that listens to your voice, processes it with an LLM, and responds with voice output using Pipecat.

## Setup

1. **Prerequisites:**
   - Python 3.10 or higher
   - Install uv (if not already installed):
     ```bash
     curl -LsSf https://astral.sh/uv/install.sh | sh
     ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

3. **Set up API keys:**
   - Create a `.env` file in the project root
   - Fill in your API keys:

   **DEEPGRAM_API_KEY** (Speech-to-Text):
   - Sign up at [https://deepgram.com/](https://deepgram.com/)
   - Go to your dashboard → API Keys
   - Create a new API key and copy it
   - Free tier available with credits

   **CARTESIA_API_KEY** (Text-to-Speech):
   - Sign up at [https://cartesia.ai/](https://cartesia.ai/)
   - Go to your dashboard → API Keys
   - Create a new API key and copy it
   - Free tier available

   **OPENAI_API_KEY** (LLM):
   - Sign up at [https://platform.openai.com/](https://platform.openai.com/)
   - Go to API Keys section
   - Create a new secret key and copy it
   - You'll need to add billing information (pay-as-you-go)

   **DAILY_ROOM_URL** and **DAILY_TOKEN** (WebRTC Transport):
   - Sign up at [https://daily.co/](https://daily.co/)
   - **Important:** Add a payment method to your account (required even for free tier)
     - Go to Dashboard → Billing → Add payment method
     - You won't be charged on the free tier, but a payment method is required
   - Go to Dashboard → Rooms
   - Create a new room (or use an existing one)
   - **Set room privacy to "public"** if you want to avoid using a token
   - Copy the room URL (should look like: `https://your-domain.daily.co/room-name`)
   - **DAILY_TOKEN is optional** - only needed for private rooms
     - For private rooms: Go to Dashboard → Developers → API Keys
     - Create a meeting token with permissions to join the room
   - Free tier available with limitations

   Example `.env` file:
   ```
   DEEPGRAM_API_KEY=your_deepgram_api_key_here
   CARTESIA_API_KEY=your_cartesia_api_key_here
   OPENAI_API_KEY=your_openai_api_key_here
   DAILY_ROOM_URL=https://your-domain.daily.co/room-name
   # DAILY_TOKEN is optional - only needed for private rooms
   # Leave it out or set to empty for public rooms
   DAILY_TOKEN=
   ```

4. **Run the bot:**
   ```bash
   uv run python voice_agent.py
   ```

## How it works

The voice bot uses a pipeline:
1. **Audio Input** → Captures your voice from microphone
2. **Speech-to-Text (STT)** → Converts speech to text using Deepgram
3. **LLM Processing** → Processes the text with OpenAI GPT-4o-mini
4. **Text-to-Speech (TTS)** → Converts the response to speech using Cartesia
5. **Audio Output** → Plays the response through speakers

## Troubleshooting

### Daily.co "account-missing-payment-method" Error
If you see this error: `RoomInfoError(Unhandled("account-missing-payment-method"))`
- This means your Daily.co account needs a payment method added
- Go to [Daily.co Dashboard](https://dashboard.daily.co/) → Billing → Add payment method
- Even on the free tier, Daily.co requires a payment method on file (you won't be charged unless you exceed free limits)

### Invalid URL Error
If you see: `Failed to parse url: InvalidUrl`
- Make sure your `DAILY_ROOM_URL` is a full URL starting with `https://`
- Format should be: `https://your-domain.daily.co/room-name`

### Timeout Errors
If you see errors like: `Timeout occurred for message` or `Failed to end timeout`
- These are often **harmless warnings** that occur during Daily connection establishment
- The agent may still work correctly despite these errors
- If the connection completely fails:
  - Check your internet connection
  - Verify the room URL is correct and the room exists
  - Try restarting the agent
  - Check Daily.co service status

## Notes

- This example uses Daily for WebRTC transport. You'll need to create a Daily room and provide the room URL and token.
- For a simpler setup without Daily, you might want to use a different transport like local audio.

