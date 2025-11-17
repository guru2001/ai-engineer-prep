"""Deepgram service for speech-to-text"""
import os
from typing import Optional
import requests
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
        logger.info("DeepgramService initialized")
    
    def transcribe_audio(self, audio_file, language: Optional[str] = None) -> str:
        """Transcribe audio file to text using Deepgram REST API
        
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
            
            # Make API request
            # Deepgram expects the audio file as raw data
            response = requests.post(
                self.base_url,
                params=params,
                headers=headers,
                data=audio_data,
                timeout=30
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
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Deepgram API request error: {e}", exc_info=True)
            raise Exception(f"Failed to transcribe audio: {str(e)}")
        except Exception as e:
            logger.error(f"Deepgram transcription error: {e}", exc_info=True)
            raise Exception(f"Failed to transcribe audio: {str(e)}")

