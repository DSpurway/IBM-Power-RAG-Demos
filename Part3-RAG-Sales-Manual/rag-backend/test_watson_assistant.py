"""
Test Watson Assistant Integration
Tests the existing Watson Assistant to understand its response format
"""

import requests
import json
import sys

# Your Watson Assistant credentials
WATSON_API_KEY = "Y-WtqYpU77yrcm7bs2xHqVKjzm9d6gLUh_4o-B0CChGJ"
WATSON_URL = "https://api.eu-gb.assistant.watson.cloud.ibm.com/instances/c6a8deb1-c724-4ad3-ac1d-660144bf8792"
WATSON_VERSION = "2021-11-27"

# Test queries
TEST_QUERIES = [
    "When did we stop supporting the S924?",
    "When was the E1180 announced?",
    "What is the MTM for the Power E1180?",
    "When did the 9080-HEU become available?",
    "Is the S1024 still supported?",
]


def create_session(assistant_id=None):
    """Create a Watson Assistant session"""
    if not assistant_id:
        print("ERROR: Assistant ID is required")
        print("Please provide it as a command line argument:")
        print(f"  python {sys.argv[0]} <assistant-id>")
        return None
    
    session_url = f"{WATSON_URL}/v2/assistants/{assistant_id}/sessions"
    
    try:
        response = requests.post(
            session_url,
            params={'version': WATSON_VERSION},
            auth=('apikey', WATSON_API_KEY),
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        session_id = data.get('session_id')
        print(f"✓ Created session: {session_id}")
        return session_id
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to create session: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def send_message(assistant_id, session_id, message):
    """Send a message to Watson Assistant"""
    message_url = f"{WATSON_URL}/v2/assistants/{assistant_id}/sessions/{session_id}/message"
    
    payload = {
        'input': {
            'message_type': 'text',
            'text': message
        }
    }
    
    try:
        response = requests.post(
            message_url,
            params={'version': WATSON_VERSION},
            auth=('apikey', WATSON_API_KEY),
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to send message: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return None


def analyze_response(query, response):
    """Analyze Watson Assistant response"""
    print(f"\n{'='*80}")
    print(f"Query: {query}")
    print(f"{'='*80}")
    
    if not response:
        print("No response received")
        return
    
    # Extract key information
    output = response.get('output', {})
    intents = output.get('intents', [])
    entities = output.get('entities', [])
    generic = output.get('generic', [])
    
    print(f"\n📊 INTENTS ({len(intents)}):")
    for intent in intents:
        print(f"  - {intent.get('intent')}: {intent.get('confidence', 0):.3f}")
    
    print(f"\n🏷️  ENTITIES ({len(entities)}):")
    for entity in entities:
        print(f"  - {entity.get('entity')}: '{entity.get('value')}' (confidence: {entity.get('confidence', 0):.3f})")
        if entity.get('location'):
            print(f"    Location: {entity.get('location')}")
    
    print(f"\n💬 RESPONSE ({len(generic)} items):")
    for item in generic:
        response_type = item.get('response_type')
        if response_type == 'text':
            print(f"  Text: {item.get('text')}")
        elif response_type == 'option':
            print(f"  Options: {item.get('title')}")
            for option in item.get('options', []):
                print(f"    - {option.get('label')}")
        else:
            print(f"  Type: {response_type}")
            print(f"  Data: {json.dumps(item, indent=4)}")
    
    # Check for context variables (Node-RED might have set these)
    context = response.get('context', {})
    if context:
        print(f"\n🔧 CONTEXT:")
        skills = context.get('skills', {})
        if skills:
            main_skill = skills.get('main skill', {})
            user_defined = main_skill.get('user_defined', {})
            if user_defined:
                print(f"  User Defined Variables:")
                for key, value in user_defined.items():
                    print(f"    - {key}: {value}")
    
    print(f"\n📄 FULL RESPONSE:")
    print(json.dumps(response, indent=2))


def test_assistant(assistant_id):
    """Test Watson Assistant with various queries"""
    print(f"\n{'='*80}")
    print(f"Testing Watson Assistant")
    print(f"{'='*80}")
    print(f"API Key: {WATSON_API_KEY[:20]}...")
    print(f"URL: {WATSON_URL}")
    print(f"Assistant ID: {assistant_id}")
    
    # Create session
    session_id = create_session(assistant_id)
    if not session_id:
        return
    
    # Test each query
    for query in TEST_QUERIES:
        response = send_message(assistant_id, session_id, query)
        analyze_response(query, response)
        print("\n" + "="*80 + "\n")
    
    print("✓ Testing complete!")


def list_assistants():
    """List available assistants (if we don't have the ID)"""
    print("\nAttempting to list assistants...")
    
    # Try to list assistants
    list_url = f"{WATSON_URL}/v2/assistants"
    
    try:
        response = requests.get(
            list_url,
            params={'version': WATSON_VERSION},
            auth=('apikey', WATSON_API_KEY),
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        assistants = data.get('assistants', [])
        
        if assistants:
            print(f"\n✓ Found {len(assistants)} assistant(s):")
            for assistant in assistants:
                print(f"  - ID: {assistant.get('assistant_id')}")
                print(f"    Name: {assistant.get('name')}")
                print(f"    Description: {assistant.get('description')}")
                print()
        else:
            print("No assistants found")
        
        return assistants
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed to list assistants: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"  Response: {e.response.text}")
        return []


if __name__ == "__main__":
    print("\n" + "="*80)
    print("Watson Assistant Test Script")
    print("="*80)
    
    # Check if assistant ID provided
    if len(sys.argv) > 1:
        assistant_id = sys.argv[1]
        test_assistant(assistant_id)
    else:
        print("\nNo Assistant ID provided. Attempting to list available assistants...")
        assistants = list_assistants()
        
        if assistants:
            print("\nTo test an assistant, run:")
            print(f"  python {sys.argv[0]} <assistant-id>")
            print("\nExample:")
            print(f"  python {sys.argv[0]} {assistants[0].get('assistant_id')}")
        else:
            print("\nCould not find assistants. You may need to:")
            print("1. Check your Watson Assistant credentials")
            print("2. Ensure you have at least one assistant created")
            print("3. Provide the assistant ID directly:")
            print(f"   python {sys.argv[0]} <your-assistant-id>")

# Made with Bob