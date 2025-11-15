"""
Simple Wikipedia Voice Bot
Ask questions and get Wikipedia answers via voice - no rooms needed!
"""

import os
import asyncio
import base64
import json
import wikipedia
import requests
from dotenv import load_dotenv
from deepgram import DeepgramClient, PrerecordedOptions, FileSource
import sounddevice as sd
import numpy as np
import wave
import tempfile

# Load environment variables
load_dotenv()

# Initialize services
deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
cartesia_api_key = os.getenv("CARTESIA_API_KEY")

if not deepgram_api_key or not cartesia_api_key:
    print("Error: Please set DEEPGRAM_API_KEY and CARTESIA_API_KEY in your .env file")
    exit(1)

deepgram = DeepgramClient(deepgram_api_key)
CARTESIA_API_KEY = cartesia_api_key

def record_audio(duration=5, sample_rate=16000):
    """Record audio from microphone"""
    print(f"\n🎤 Listening for {duration} seconds... Speak now!")
    audio_data = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype='float32')
    sd.wait()  # Wait until recording is finished
    return audio_data, sample_rate

def save_audio_to_file(audio_data, sample_rate):
    """Save audio data to temporary WAV file"""
    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
        filename = tmp_file.name
        with wave.open(filename, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            # Convert float32 to int16
            audio_int16 = (audio_data * 32767).astype(np.int16)
            wav_file.writeframes(audio_int16.tobytes())
        return filename

def speech_to_text(audio_file):
    """Convert speech to text using Deepgram"""
    try:
        with open(audio_file, "rb") as file:
            buffer_data = file.read()
        
        payload: FileSource = {
            "buffer": buffer_data,
        }
        
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
        )
        
        response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
        transcript = response.results.channels[0].alternatives[0].transcript
        return transcript.strip()
    except Exception as e:
        print(f"Error in speech-to-text: {e}")
        return None

def extract_topic(question):
    """Extract the main topic from a question"""
    # Remove common question words and phrases
    question_lower = question.lower().strip()
    
    # Remove question starters
    question_starters = [
        "tell me about", "what is", "who is", "what are", "who are",
        "explain", "describe", "hey", "hi", "hello", "can you tell me",
        "i want to know about", "tell me", "what do you know about"
    ]
    
    for starter in question_starters:
        if question_lower.startswith(starter):
            question_lower = question_lower[len(starter):].strip()
            # Remove trailing punctuation
            question_lower = question_lower.rstrip(".,!?")
            break
    
    # If the question is just "about X", extract X
    if question_lower.startswith("about "):
        question_lower = question_lower[6:].strip()
    
    # Take the first meaningful phrase (before any punctuation or "and", "or", etc.)
    topic = question_lower.split(",")[0].split(" and ")[0].split(" or ")[0].split("?")[0].strip()
    
    # Capitalize first letter of each word for better Wikipedia search
    topic = topic.title()
    
    return topic if topic else question.strip()

def search_wikipedia(query):
    """Search Wikipedia and get summary"""
    try:
        # Extract the main topic from the question
        topic = extract_topic(query)
        print(f"🔎 Searching for: {topic}")
        
        # Search for the page
        search_results = wikipedia.search(topic, results=1)
        if not search_results:
            return f"Sorry, I couldn't find information about '{topic}' on Wikipedia."
        
        # Get the page
        page = wikipedia.page(search_results[0])
        summary = page.summary[:500]  # Limit to 500 characters for voice response
        return f"According to Wikipedia: {summary}"
    except wikipedia.exceptions.DisambiguationError as e:
        # If there's a disambiguation, use the first option
        try:
            page = wikipedia.page(e.options[0])
            summary = page.summary[:500]
            return f"According to Wikipedia: {summary}"
        except:
            return f"Multiple results found for '{topic}'. Could you be more specific?"
    except wikipedia.exceptions.PageError:
        return f"Sorry, I couldn't find a Wikipedia page for '{topic}'."
    except Exception as e:
        return f"Error searching Wikipedia: {str(e)}"

def text_to_speech(text):
    """Convert text to speech using Cartesia SSE API"""
    try:
        print(f"🔊 Speaking: {text[:100]}...")
        
        # Use Cartesia SSE API endpoint
        url = "https://api.cartesia.ai/tts/sse"
        headers = {
            "Cartesia-Version": "2025-04-16",
            "X-API-Key": CARTESIA_API_KEY,
            "Content-Type": "application/json"
        }
        data = {
            "model_id": "sonic-english",
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": "79a125e8-cd45-4c13-8a67-188112f4dd22"
            },
            "language": "en",
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": 16000
            }
        }
        
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        # Collect audio chunks from SSE stream
        # Cartesia sends JSON objects with type="chunk" and data field containing base64 audio
        audio_chunks = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    # Extract data after 'data: ' prefix
                    data_str = line_str[6:].strip()
                    if data_str and data_str != '[DONE]':
                        try:
                            # Parse as JSON (Cartesia SSE format)
                            json_data = json.loads(data_str)
                            
                            # Check if it's a chunk with audio data
                            if isinstance(json_data, dict) and json_data.get('type') == 'chunk':
                                if 'data' in json_data and isinstance(json_data['data'], str):
                                    # Decode base64 audio data
                                    audio_chunk = base64.b64decode(json_data['data'])
                                    audio_chunks.append(audio_chunk)
                        except (json.JSONDecodeError, KeyError, ValueError) as e:
                            # Skip non-audio chunks or invalid data
                            pass
        
        # Combine all audio chunks
        if audio_chunks:
            audio_bytes = b''.join(audio_chunks)
            
            # Ensure buffer size is a multiple of 2 (int16 = 2 bytes)
            if len(audio_bytes) % 2 != 0:
                audio_bytes = audio_bytes[:-1]  # Remove last byte if odd
            
            if len(audio_bytes) > 0:
                # Convert response to numpy array and play
                # Note: pcm_s16le is little-endian signed 16-bit PCM
                audio_data = np.frombuffer(audio_bytes, dtype=np.int16)
                # Convert to float32 and normalize to [-1, 1]
                audio_data = audio_data.astype(np.float32) / 32768.0
                
                sd.play(audio_data, samplerate=16000)
                sd.wait()  # Wait until playback is finished
            else:
                print("No valid audio data received from Cartesia")
        else:
            print("No audio data received from Cartesia")
    except Exception as e:
        print(f"Error in text-to-speech: {e}")
        import traceback
        traceback.print_exc()

async def main():
    print("\n" + "="*60)
    print("📚 Wikipedia Voice Bot")
    print("="*60)
    print("Ask me anything and I'll search Wikipedia for you!")
    print("Press Ctrl+C to exit")
    print("="*60 + "\n")
    
    while True:
        try:
            # Record audio
            audio_data, sample_rate = record_audio(duration=5)
            
            # Save to temporary file
            audio_file = save_audio_to_file(audio_data, sample_rate)
            
            # Convert speech to text
            print("🔄 Processing your question...")
            question = speech_to_text(audio_file)
            
            # Clean up temp file
            os.unlink(audio_file)
            
            if not question:
                print("❌ Could not understand your question. Please try again.")
                continue
            
            print(f"❓ Your question: {question}")
            
            # Search Wikipedia
            print("🔍 Searching Wikipedia...")
            answer = search_wikipedia(question)
            print(f"📖 Answer: {answer}\n")
            
            # Convert answer to speech
            text_to_speech(answer)
            
            print("\n" + "-"*60 + "\n")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            continue

if __name__ == "__main__":
    asyncio.run(main())

