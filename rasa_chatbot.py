import asyncio
from rasa.core.agent import Agent

# Replace this path with the location of your trained model
MODEL_PATH = "C:\Users\hisha\Documents\CSCI_4385\models\ARGUS.tar.gz"

# Load the Rasa agent asynchronously when this module is imported.
# (This can take some time, so you may wish to handle it appropriately.)
agent = Agent.load(MODEL_PATH)

def get_response(message: str) -> str:
    """
    Uses the loaded Rasa agent to process a message and return a response.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    responses = loop.run_until_complete(agent.handle_text(message))
    loop.close()
    
    # Extract and return the first text response, if available.
    if responses and isinstance(responses, list) and "text" in responses[0]:
        return responses[0]["text"]
    return "I'm sorry, I didn't understand that."