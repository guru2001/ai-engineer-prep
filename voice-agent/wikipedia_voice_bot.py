"""
Simple Wikipedia Voice Bot
Mic -> STT -> Wikipedia -> TTS -> Speaker
"""

import asyncio
import os
import wikipedia
from dotenv import load_dotenv

from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.task import PipelineTask, PipelineParams, PipelineTaskParams
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.frames.frames import StartFrame, TextFrame
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.openai.tts import OpenAITTSService
from pipecat.transports.smallwebrtc.transport import SmallWebRTCTransport, TransportParams
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.runner.types import RunnerArguments

load_dotenv()


# ----------------- WIKIPEDIA HELPERS ----------------- #

def extract_topic(question: str) -> str:
    q = question.lower().strip()

    starters = [
        "tell me about", "what is", "who is", "what are", "who are",
        "explain", "describe", "can you tell me",
        "i want to know about", "tell me", "what do you know about",
        "hey", "hi", "hello"
    ]

    for s in starters:
        if q.startswith(s):
            q = q[len(s):].strip()
            break

    if q.startswith("about "):
        q = q[6:].strip()

    topic = (
        q.split(",")[0]
        .split(" and ")[0]
        .split(" or ")[0]
        .split("?")[0]
        .strip()
    )

    return topic.title() if topic else question.strip()


def search_wikipedia(query: str) -> str:
    try:
        topic = extract_topic(query)
        print(f"🔎 Searching Wikipedia for: {topic}")

        results = wikipedia.search(topic, results=1)

        if not results:
            return f"Sorry, I couldn't find anything about {topic}."

        page = wikipedia.page(results[0])
        return f"According to Wikipedia: {page.summary[:500]}"

    except wikipedia.exceptions.DisambiguationError as e:
        page = wikipedia.page(e.options[0])
        return f"According to Wikipedia: {page.summary[:500]}"

    except Exception as e:
        return f"Error: {str(e)}"


# ----------------- CUSTOM PROCESSOR ----------------- #

class WikipediaProcessor(FrameProcessor):
    async def process_frame(self, frame, direction):
        # Always call parent first to handle initialization
        await super().process_frame(frame, direction)

        # Only process TextFrame (user questions)
        if isinstance(frame, TextFrame):
            question = frame.text.strip()
            
            # Skip empty text
            if not question:
                await self.push_frame(frame, direction)
                return
            
            print(f"\n❓ User asked: {question}")

            answer = search_wikipedia(question)
            print(f"📘 Answer: {answer}\n")

            # Push the answer as a new TextFrame
            await self.push_frame(TextFrame(answer), direction)
            return

        # Forward all other frames (StartFrame, AudioFrame, etc.)
        await self.push_frame(frame, direction)


# ----------------- BOT SETUP ----------------- #

async def run_bot(transport: SmallWebRTCTransport):
    """Set up and run the Wikipedia bot pipeline."""
    
    print("🔧 Setting up pipeline...")
    
    # STT
    stt = OpenAISTTService(
        model="gpt-4o-transcribe",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    print("✅ STT service initialized")

    # TTS
    tts = OpenAITTSService(
        voice="alloy",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    print("✅ TTS service initialized")

    wiki = WikipediaProcessor()
    print("✅ Wikipedia processor initialized")

    # Pipeline
    pipeline = Pipeline([
        transport.input(),   # microphone
        stt,                 # speech → text
        wiki,                # wikipedia query
        tts,                 # text → speech
        transport.output()   # speaker
    ])
    print("✅ Pipeline created")

    # Create pipeline task with parameters
    pipeline_params = PipelineParams(
        audio_in_sample_rate=16000,
        audio_out_sample_rate=16000,
    )
    
    task = PipelineTask(pipeline, params=pipeline_params)
    print("✅ Pipeline task created")
    
    # Queue the StartFrame to initialize the pipeline
    await task.queue_frames([StartFrame()])
    print("✅ StartFrame queued")
    
    print("🎤 Bot is ready! Speak your question...")
    
    # Create task params with the running event loop
    task_params = PipelineTaskParams(loop=asyncio.get_running_loop())
    
    # Run the pipeline task
    await task.run(task_params)


# ----------------- RUNNER ENTRY POINT ----------------- #

async def bot(runner_args: RunnerArguments):
    """Main bot entry point called by the development runner."""
    
    # Create your transport based on the runner arguments
    transport = SmallWebRTCTransport(
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
        webrtc_connection=runner_args.webrtc_connection,
    )

    # Run your bot logic
    await run_bot(transport)


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()
