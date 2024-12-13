from openai import OpenAI

# Set OpenAI API key
client = OpenAI(api_key="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")  # Replace with your actual API key
GPT_MODEL = "gpt-4-1106-preview"  

def is_product_query(user_input):
    """Check if the input is likely a product query."""
    keywords = ["price", "color", "product", "size", "availability", "buy", "order"]
    return any(keyword in user_input.lower() for keyword in keywords) or len(user_input.split()) > 2


def get_ai_response(user_input):
    """Get a response from OpenAI GPT."""
    try:
        messages = [
            {"role": "system", "content": "You are a helpful e-commerce chatbot that can answer questions about products and gives a genaric description when asked on any product."},
            {"role": "user", "content": user_input}
        ]
        response = client.chat.completions.create(
            model=GPT_MODEL,
            messages=messages,
            temperature=1
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return "Sorry, I'm having trouble understanding you right now."

