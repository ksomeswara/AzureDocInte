from openai import OpenAI
import os

class OpenAIChat:
    def __init__(self):
        """
        Initializes the OpenAI client using the API key from environment variables.
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set or accessible")
        self.client = OpenAI(api_key=self.api_key)

    def generate_completion(self, model: str, messages: list):
        """
        Sends a chat completion request to the OpenAI API.

        Args:
            model (str): The model to use (e.g., 'gpt-4o-mini').
            messages (list): List of message dictionaries with roles ('system', 'user', 'assistant') and content.

        Returns:
            dict: The completion response from the OpenAI API.
        """
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages
            )
            return response.choices[0].message
        except Exception as e:
            raise RuntimeError(f"Failed to generate completion: {str(e)}")

# Usage example
# if __name__ == "__main__":
#     try:
#         chat = OpenAIChat()
#         model = "gpt-4o-mini"
#         messages = [
#             {"role": "system", "content": "You are a helpful assistant."},
#             {"role": "user", "content": "Write a haiku about recursion in programming."}
#         ]
#         result = chat.generate_completion(model, messages)
#         print("Generated Completion:")
#         print(result)
#     except Exception as e:
#         print(f"Error: {str(e)}")
