# Optional ElevenLabs voice on macOS

Usama keeps Gemini Live for listening, reasoning and tool calls. ElevenLabs can
replace its *spoken replies* when a voice ID and API key are configured. If the
ElevenLabs request fails, the original Gemini audio is used as a fallback.
No extra pip package is needed; the existing requests dependency is used.

1. Choose or create a voice that you have permission to use in ElevenLabs.
   Copy its Voice ID from your ElevenLabs account.
2. On your own Mac, open the existing ignored file config/api_keys.json.
   Add these three keys without deleting the existing Gemini key or other data:

    "elevenlabs_api_key": "YOUR_PRIVATE_ELEVENLABS_API_KEY",
    "elevenlabs_voice_id": "YOUR_VOICE_ID",
    "elevenlabs_model_id": "eleven_multilingual_v2"

3. Save and restart Usama. The activity feed should show
   "Optional ElevenLabs voice enabled."

Alternatively, set ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in Usama's process
environment. ELEVENLABS_MODEL_ID is optional.

The fixed startup line remains "Hi, my name is Osama." The welcome's 24 kHz
PCM is cached locally under ~/.usama/voice_cache/ to avoid a repeated API call.
Personal conversations are NOT written into that voice cache.

Custom TTS is an optional setting, not a free feature. ElevenLabs requires
network access and may charge for generated speech. Because the integration
generates audio after a complete Gemini response, it can be slower than Gemini
Live's native streaming voice. Remove the ElevenLabs key/voice ID and restart
to return to Gemini's existing voice.

Do not paste API keys into GitHub, screenshots, or chat. The config file is
ignored by Git, but check before sharing any local files.
