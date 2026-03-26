'''
Text-to-Speech utility using Sarvam AI

This module provides the utility function for converting text to speech
using the Sarvam AI SDK.
'''

import os
import base64


def sarvam_tts(text, language_code='en-IN', config=None):
    """
    Convert text to speech using Sarvam AI SDK.
    
    Args:
        text (str): The text to convert to speech
        language_code (str): Language code (e.g., 'en-IN', 'hi-IN', 'ta-IN')
        config (AIAPIConfiguration, optional): The configuration object containing API details
        
    Returns:
        dict: Dictionary containing:
            - 'audio_data': bytes - Decoded WAV audio data
            - 'request_id': str - Request ID from Sarvam API (if available)
            - 'format': str - Audio format (always 'wav')
        
    Raises:
        ValueError: If configuration is invalid or text is empty
        Exception: If API call fails
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")
    
    # Import Sarvam AI SDK
    try:
        from sarvamai import SarvamAI
    except ImportError:
        raise ImportError("Sarvam AI SDK not installed. Please install it with: pip install sarvamai")
    
    # Get API key from configuration or environment
    if config:
        if not config.api_key_environment_variable_name:
            raise ValueError("API key environment variable name is required")
        
        api_key = os.environ.get(config.api_key_environment_variable_name)
        if not api_key:
            raise ValueError(f"API key not found in environment variable: {config.api_key_environment_variable_name}")
    else:
        # Fallback to environment variables
        api_key = os.environ.get('SARVAM_API_KEY')
        if not api_key:
            raise ValueError("SARVAM_API_KEY environment variable not set")
    
    # Initialize Sarvam AI client
    client = SarvamAI(api_subscription_key=api_key)
    
    # Map language codes to appropriate speakers
    speaker_map = {
        'en-IN': 'ritu',
        'hi-IN': 'ritu',
        'ta-IN': 'ritu',
        'te-IN': 'ritu',
        'kn-IN': 'ritu',
        'ml-IN': 'ritu',
        'mr-IN': 'ritu',
        'gu-IN': 'ritu',
        'bn-IN': 'ritu',
        'pa-IN': 'ritu',
    }
    
    speaker = speaker_map.get(language_code, 'ritu')
    
    try:
        # Call Sarvam AI TTS API using SDK
        response = client.text_to_speech.convert(
            text=text,
            target_language_code=language_code,
            speaker=speaker,
            pace=0.9,
            enable_preprocessing=True,
            model="bulbul:v3"
        )
        
        # The SDK response contains base64 encoded audio in 'audios' field
        if hasattr(response, 'audios') and response.audios:
            # Decode base64 audio data (first audio in list)
            base64_audio = response.audios[0]
            audio_bytes = base64.b64decode(base64_audio)
            
            return {
                'audio_data': audio_bytes,
                'request_id': getattr(response, 'request_id', None),
                'format': 'wav'
            }
        else:
            raise ValueError("No audio data in response from Sarvam AI")
        
    except Exception as e:
        raise Exception(f"Sarvam AI TTS failed: {str(e)}")