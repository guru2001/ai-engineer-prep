"""Deepgram service for speech-to-text"""
import os
from typing import Optional
import httpx
from logger_config import logger


class DeepgramService:
    """Service for transcribing audio using Deepgram API"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Deepgram service
        
        Args:
            api_key: Deepgram API key (optional, falls back to env var)
        """
        api_key = api_key or os.getenv("DEEPGRAM_API_KEY")
        if not api_key:
            raise ValueError("Deepgram API key is required. Set DEEPGRAM_API_KEY environment variable.")
        
        self.api_key = api_key
        self.base_url = "https://api.deepgram.com/v1/listen"
        # Create a persistent async HTTP client with connection pooling
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20)
        )
        logger.info("DeepgramService initialized with async HTTP client")
    
    async def transcribe_audio(self, audio_file, language: Optional[str] = None) -> str:
        """Transcribe audio file to text using Deepgram REST API (async)
        
        Args:
            audio_file: File-like object (BytesIO) containing audio data
            language: Language code (e.g., 'en', 'es', 'fr'). Optional, auto-detects if not provided.
            
        Returns:
            Transcribed text string
        """
        try:
            # Reset file pointer to beginning
            if hasattr(audio_file, 'seek'):
                audio_file.seek(0)
            
            # Read file content
            audio_data = audio_file.read()
            
            logger.debug(f"Transcribing audio with Deepgram (language: {language or 'auto-detect'})")
            
            # Prepare request parameters
            params = {
                'model': 'nova-2',
                'smart_format': 'true',
            }
            
            if language:
                params['language'] = language
            
            # Prepare headers
            headers = {
                'Authorization': f'Token {self.api_key}',
                'Content-Type': 'audio/webm',  # Adjust based on actual audio format
            }
            
            # Make async API request
            # Deepgram expects the audio file as raw data
            response = await self.client.post(
                self.base_url,
                params=params,
                headers=headers,
                content=audio_data
            )
            
            # Check response
            response.raise_for_status()
            result = response.json()
            
            # Extract transcript
            if result.get('results') and result['results'].get('channels'):
                transcript = result['results']['channels'][0]['alternatives'][0]['transcript']
                text = transcript.strip()
                logger.info(f"Deepgram transcription successful: {text[:50]}...")
                return text
            else:
                raise Exception("No transcript found in Deepgram response")
            
        except httpx.HTTPError as e:
            logger.error(f"Deepgram API request error: {e}", exc_info=True)
            raise Exception(f"Failed to transcribe audio: {str(e)}")
        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}", exc_info=True)
            raise Exception(f"Failed to transcribe audio: {str(e)}")
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

