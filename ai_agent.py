import os
from google import genai
from google.genai import types
from openai import OpenAI
from dotenv import load_dotenv

# Load variables from your .env file
load_dotenv()

def analyze_schedule(logs_df, user_query):
    """
    Attempts to use Google Gemini for log analysis. 
    Automatically falls back to OpenRouter's auto-routing free tier if Gemini fails.
    """
    gemini_key = os.environ.get("GEMINI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    
    log_data_json = logs_df.to_json(orient="records")
    prompt = f"""
    Here is the execution history of a CPU scheduler in JSON format: 
    {log_data_json}
    
    The user has a question about this schedule: "{user_query}"
    """
    
    system_instruction = (
        "You are an expert Operating Systems professor and debugger. "
        "Analyze the provided CPU scheduler logs. Explain concepts clearly, "
        "point out any process starvation or excessive context switching, "
        "and suggest specific parameter tweaks to fix it."
    )

    # ==========================================
    # Attempt 1: Google Gemini
    # ==========================================
    if gemini_key:
        try:
            gemini_client = genai.Client(api_key=gemini_key)
            config = types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.3
            )
            response = gemini_client.models.generate_content(
                model="gemini-3.8-flash",
                contents=prompt,
                config=config
            )
            return f"**[Powered by Gemini]**\n\n{response.text}"
            
        except Exception as e:
            print(f"Gemini API failed: {e}. Triggering OpenRouter fallback...")

    # ==========================================
    # Attempt 2: OpenRouter Auto-Fallback
    # ==========================================
    if openrouter_key:
        try:
            # We use the standard OpenAI client but point it to OpenRouter
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key
            )
            response = client.chat.completions.create(
                model="openrouter/free", # Automatically picks a working free model
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            return f"**[Powered by OpenRouter Backup]**\n\n{response.choices[0].message.content}"
            
        except Exception as e:
            return f"Error: Both APIs failed.\nOpenRouter Error: {e}"
            
    return "Error: Missing API keys in .env file."