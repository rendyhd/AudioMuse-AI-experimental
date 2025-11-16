import requests
import json
import re
import ftfy # Import the ftfy library
import time # Import the time library
import logging
import unicodedata
import google.generativeai as genai # Import Gemini library
from mistralai import Mistral
import os # Import os to potentially read GEMINI_API_CALL_DELAY_SECONDS

logger = logging.getLogger(__name__)

# creative_prompt_template is imported in tasks.py, so it should be defined here
creative_prompt_template = (
    "You're an expert of music and you need to give a title to this playlist.\n"
    "The title need to represent the mood and the activity of when you listening the playlist.\n"
    "The title MUST use ONLY standard ASCII (a-z, A-Z, 0-9, spaces, and - & ' ! . , ? ( ) [ ]).\n"
    "No special fonts or emojis.\n"
    "* BAD EXAMPLES: 'Ambient Electronic Space - Electric Soundscapes - Emotional Waves' (Too long/descriptive)\n"
    "* BAD EXAMPLES: 'Blues Rock Fast Tracks' (Too direct/literal, not evocative enough)\n"
    "* BAD EXAMPLES: '𝑯𝒘𝒆 𝒂𝒓𝒐𝒏𝒊 𝒅𝒆𝒕𝒔' (Non-standard characters)\n\n"
    "CRITICAL: Your response MUST be ONLY the single playlist name. No explanations, no 'Playlist Name:', no numbering, no extra text or formatting whatsoever.\n"
    "This is the playlist: {song_list_sample}\n\n" # {song_list_sample} will contain the full list

)

def clean_playlist_name(name):
    if not isinstance(name, str):
        return ""
    # print(f"DEBUG CLEAN AI: Input name: '{name}'") # Print name before cleaning

    name = ftfy.fix_text(name)

    name = unicodedata.normalize('NFKC', name)
    # Stricter regex: only allows characters explicitly mentioned in the prompt.
    cleaned_name = re.sub(r'[^a-zA-Z0-9\s\-\&\'!\.\,\?\(\)\[\]]', '', name)
    # Also remove trailing number in parentheses, e.g., "My Playlist (2)" -> "My Playlist", to prevent AI from interfering with disambiguation logic.
    cleaned_name = re.sub(r'\s\(\d+\)$', '', cleaned_name)
    cleaned_name = re.sub(r'\s+', ' ', cleaned_name).strip()
    return cleaned_name


# --- OpenAI Compatible Function (for Ollama, OpenRouter, etc.) ---
def get_openai_playlist_name(server_url, model_name, api_key, full_prompt):
    """
    Calls an OpenAI-compatible API to get a playlist name.

    Args:
        server_url (str): The URL of the OpenAI-compatible API endpoint.
        model_name (str): The model to use.
        api_key (str): The API key for authentication.
        full_prompt (str): The complete prompt text to send to the model.
    Returns:
        str: The extracted playlist name from the model's response, or an error message.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": full_prompt}
        ],
        "temperature": 0.9,
        "max_tokens": 50,
    }

    try:
        logger.debug("Starting API call for model '%s' at '%s'.", model_name, server_url)
        response = requests.post(server_url, headers=headers, data=json.dumps(payload), timeout=960)
        response.raise_for_status()

        response_data = response.json()

        if response_data.get("choices") and response_data["choices"][0].get("message"):
            extracted_text = response_data["choices"][0]["message"].get("content", "").strip()
            return extracted_text
        else:
            logger.error("Invalid response format from OpenAI API: %s", response_data)
            return "Error: Invalid response from AI service."

    except requests.exceptions.RequestException as e:
        logger.error("Error calling OpenAI API: %s", e, exc_info=True)
        return "Error: AI service is currently unavailable."
    except Exception as e:
        logger.error("An unexpected error occurred in get_openai_playlist_name", exc_info=True)
        return "Error: AI service is currently unavailable."

# --- Gemini Specific Function ---
def get_gemini_playlist_name(gemini_api_key, model_name, full_prompt):
    """
    Calls the Google Gemini API to get a playlist name.

    Args:
        gemini_api_key (str): Your Google Gemini API key.
        model_name (str): The Gemini model to use (e.g., "gemini-2.5-pro").
        full_prompt (str): The complete prompt text to send to the model.
    Returns:
        str: The extracted playlist name from the model's response, or an error message.
    """
    # Allow any provided key, even if it's the placeholder, but check if it's empty/default
    if not gemini_api_key or gemini_api_key == "YOUR-GEMINI-API-KEY-HERE":
         return "Error: Gemini API key is missing or empty. Please provide a valid API key."
    
    try:
        # Read delay from environment/config if needed, otherwise use the default
        gemini_call_delay = int(os.environ.get("GEMINI_API_CALL_DELAY_SECONDS", "7")) # type: ignore
        if gemini_call_delay > 0:
            logger.debug("Waiting for %ss before Gemini API call to respect rate limits.", gemini_call_delay)
            time.sleep(gemini_call_delay)

        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel(model_name)

        logger.debug("Starting API call for model '%s'.", model_name)
 
        generation_config = genai.types.GenerationConfig(
            temperature=0.9 # Explicitly set temperature for more creative/varied responses
        )
        response = model.generate_content(full_prompt, generation_config=generation_config, request_options={'timeout': 960})
        # Extract text from the response # type: ignore
        if response and response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            extracted_text = "".join(part.text for part in response.candidates[0].content.parts)
        else:
            logger.debug("Gemini returned no content. Raw response: %s", response)
            return "Error: Gemini returned no content."

        # The final cleaning and length check is done in the general function
        return extracted_text

    except Exception as e:
        logger.error("Error calling Gemini API: %s", e, exc_info=True)
        return "Error: AI service is currently unavailable."

# --- Mistral Specific Function ---
def get_mistral_playlist_name(mistral_api_key, model_name, full_prompt):
    """
    Calls the Mistral API to get a playlist name.

    Args:
        mistral_api_key (str): Your Mistral API key.
        model_name (str): The mistral model to use (e.g., "ministral-3b-latest").
        full_prompt (str): The complete prompt text to send to the model.
    Returns:
        str: The extracted playlist name from the model's response, or an error message.
    """
    # Allow any provided key, even if it's the placeholder, but check if it's empty/default
    if not mistral_api_key or mistral_api_key == "YOUR-MISTRAL-API-KEY-HERE":
         return "Error: Mistral API key is missing or empty. Please provide a valid API key."

    try:
        # Read delay from environment/config if needed, otherwise use the default
        mistral_call_delay = int(os.environ.get("MISTRAL_API_CALL_DELAY_SECONDS", "7")) # type: ignore
        if mistral_call_delay > 0:
            logger.debug("Waiting for %ss before mistral API call to respect rate limits.", mistral_call_delay)
            time.sleep(mistral_call_delay)

        client = Mistral(api_key=mistral_api_key)

        logger.debug("Starting API call for model '%s'.", model_name)

        response = client.chat.complete(model=model_name,
                                        temperature=0.9,
                                        timeout_ms=960,
                                        messages=[
                                            {
                                                "role": "user",
                                                "content": full_prompt,
                                            },
                                        ])
        # Extract text from the response # type: ignore
        if response and response.choices[0].message.content:
            extracted_text = response.choices[0].message.content
        else:
            logger.debug("Mistral returned no content. Raw response: %s", response)
            return "Error: mistral returned no content."

        # The final cleaning and length check is done in the general function
        return extracted_text

    except Exception as e:
        logger.error("Error calling Mistral API: %s", e, exc_info=True)
        return "Error: AI service is currently unavailable."

# --- General AI Naming Function ---
def get_ai_playlist_name(provider, openai_server_url, openai_model_name, openai_api_key, gemini_api_key, gemini_model_name, mistral_api_key, mistral_model_name, prompt_template, feature1, feature2, feature3, song_list, other_feature_scores_dict):
    """
    Selects and calls the appropriate AI model based on the provider.
    Constructs the full prompt including new features.
    Applies length constraints after getting the name.
    """
    MIN_LENGTH = 15
    MAX_LENGTH = 40

    # --- Prepare feature descriptions for the prompt ---
    tempo_description_for_ai = "Tempo is moderate." # Default
    energy_description = "" # Initialize energy description

    if other_feature_scores_dict:
        # Extract energy score first, as it's handled separately
        # Check for 'energy_normalized' first, then fall back to 'energy'
        energy_score = other_feature_scores_dict.get('energy_normalized', other_feature_scores_dict.get('energy', 0.0))

        # Create energy description based on score (example thresholds)
        if energy_score < 0.3:
            energy_description = " It has low energy."
        elif energy_score > 0.7:
            energy_description = " It has high energy."
        # No description if medium energy (between 0.3 and 0.7)

        # Create tempo description
        tempo_normalized_score = other_feature_scores_dict.get('tempo_normalized', 0.5) # Default to moderate if not found
        if tempo_normalized_score < 0.33:
            tempo_description_for_ai = "The tempo is generally slow."
        elif tempo_normalized_score < 0.66:
            tempo_description_for_ai = "The tempo is generally medium."
        else:
            tempo_description_for_ai = "The tempo is generally fast."

        # Note: The logic for 'new_features_description' (which was for 'additional_features_description')
        # has been removed as per the request. If you want to include other features
        # (like danceable, aggressive, etc.) in the prompt, you'd add logic here to create
        # a description for them and a corresponding placeholder in the prompt_template.

    # Format the full song list for the prompt
    formatted_song_list = "\n".join([f"- {song.get('title', 'Unknown Title')} by {song.get('author', 'Unknown Artist')}" for song in song_list]) # Send all songs

    # Construct the full prompt using the template and all features
    # The new prompt only requires the song list sample # type: ignore
    full_prompt = prompt_template.format(song_list_sample=formatted_song_list)

    logger.info("Sending prompt to AI (%s):\n%s", provider, full_prompt)

    # --- Call the AI Model ---
    name = "AI Naming Skipped" # Default if provider is NONE or invalid

    if provider in ["OLLAMA", "OPENAI"]:
        name = get_openai_playlist_name(openai_server_url, openai_model_name, openai_api_key, full_prompt)
    elif provider == "GEMINI":
        name = get_gemini_playlist_name(gemini_api_key, gemini_model_name, full_prompt)
    elif provider == "MISTRAL":
        name = get_mistral_playlist_name(mistral_api_key, mistral_model_name, full_prompt)
    # else: provider is NONE or invalid, name remains "AI Naming Skipped"

    # Apply length check and return final name or error
    # Only apply length check if a name was actually generated (not the skip message or an API error message)
    if name not in ["AI Naming Skipped"] and not name.startswith("Error"):
        cleaned_name = clean_playlist_name(name)
        if MIN_LENGTH <= len(cleaned_name) <= MAX_LENGTH:
            return cleaned_name
        else:
            # Return an error message indicating the length issue, but include the cleaned name for debugging
            return f"Error: AI generated name '{cleaned_name}' ({len(cleaned_name)} chars) outside {MIN_LENGTH}-{MAX_LENGTH} range."
    else:
        # Return the original skip message or API error message
        return name