import openai

# Predefined scenarios
SCENARIOS = [
    "summarize the text",
    "Create new products or formulations",
    "general query",
    "others"
]

# Function to categorize input text
def categorize_text(api_key, input_text, model):
    # openai.api_key = api_key
    client = openai.OpenAI(
    api_key=api_key,  # This is the default and can be omitted
    )
    # Define the prompt for categorization
    prompt = f"""
            You are an intelligent assistant. Categorize the given text into one of the predefined scenarios:
            {', '.join(SCENARIOS)}.

            Text: "{input_text}"

            Provide the most suitable category from the list above If you dont find anything suitable, select category as 'others'
            but do not provide anything else as response from outside given categories.
            """
    
    # Call OpenAI API
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a scenario categorization assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0  # Low temperature for deterministic results
    )
    
    # Extract the category from the response
    category = response.choices[0].message.content.strip()
    return category