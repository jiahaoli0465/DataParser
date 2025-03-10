from openai import OpenAI
import os
import json
from typing import Dict, Any, List
from dotenv import load_dotenv
import re

class DeepSeekProcessor:
    """
    A general-purpose DeepSeek API processor for text processing tasks.
    This class provides a basic structure that can be modified later for specific processing needs.
    """
    
    def __init__(self):
        """Initialize the DeepSeek processor with API credentials."""
        load_dotenv()
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        if not self.api_key:
            raise ValueError("Missing DEEPSEEK_API_KEY environment variable")
            
        print(f"Initializing DeepSeek client with API key starting with: {self.api_key[:4]}...")
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com"
        )
    
    def extract_items(self, text: str) -> Dict[str, Any]:
        """
        Extract names of people and assets from text using DeepSeek's API.
        
        Args:
            text: The text content to extract names and assets from
            
        Returns:
            A dictionary containing the reasoning, extracted names, and assets
        """
        try:
            # Create a prompt for extracting names and assets
            system_prompt = """You are an expert at extracting information from text. Your task is to extract:
1. Names of people
2. Assets with their details (category, value, owners, and values per owner)

IMPORTANT: Accuracy is critical. Take your time to carefully analyze the text and follow these guidelines:

For extracting names of people:
- Look for proper nouns that clearly refer to individuals
- For each person, extract both the first name and last name separately
- Assign a unique identifier (P1, P2, P3, etc.) to each person in the order they are identified
- Remove all titles (Dr., Mr., Mrs., etc.) and professional designations
- Distinguish between people's names and organization/company names
- Be careful with ambiguous names that might refer to places or things
- Only include names that are definitely people, not potential or hypothetical people
- If a name appears multiple times with different spellings or formats, standardize it

For extracting assets:
- An asset must have clear ownership by one or more people
- Categorize assets accurately by the type assigned
- Extract precise values when available
- Ensure ownership attribution is correct using the person identifiers (P1, P2, etc.)
- For shared assets, accurately distribute values among owners using their identifiers
- Look for specific descriptors that indicate asset type and value
- Be careful with hypothetical or future assets that don't currently exist
- Only include assets that are definitely owned, not potential or desired assets

Your response should be structured in three parts:
1. <reasoning>: Provide detailed reasoning about your extraction process. Explain how you identified each name and asset, any challenges you encountered, and how you resolved ambiguities. This should be comprehensive and show your analytical process.
2. <name>: Provide a JSON array containing all names of people found in the text. Each name should be an object with "id", "firstname" and "lastname" fields.
3. <asset>: Provide a JSON array of assets with their details. Each asset should include:
   - name: The name or description of the asset
   - category: The type of asset (e.g., real estate, vehicle, financial, etc.)
   - value: The total value of the asset (if available)
   - owners: Array of person identifiers (e.g., ["P1", "P2"]) who own the asset
   - valuesPerOwner: Object mapping person identifiers to their share value (e.g., {"P1": 600000, "P2": 600000})

Example format:
<reasoning>
I carefully analyzed the text to identify names and assets:

NAMES:
1. P1: John Smith - Clearly identified as a person because he is described as the owner of property. I extracted "John" as the firstname and "Smith" as the lastname.
2. P2: Jane Doe - Mentioned as co-owner of the beach house and referred to with personal pronouns. I extracted "Jane" as the firstname and "Doe" as the lastname.
3. P3: Robert Johnson - Originally mentioned as "Dr. Johnson", but I've removed the title and extracted "Robert" as the firstname and "Johnson" as the lastname.

I excluded "Highland Corporation" because it's a company name, not a person. I also removed the title "Dr." from "Dr. Johnson" to extract just the firstname and lastname.

ASSETS:
1. Beach House:
   - Categorized as "Real Estate" based on its description as a property
   - Value determined to be $1,200,000 from explicit statement "valued at $1.2 million"
   - Ownership is split equally between P1 (John Smith) and P2 (Jane Doe) as stated in "50-50 ownership"
   - Each owner has a $600,000 share based on the equal split

2. Investment Portfolio:
   - Categorized as "Financial" based on description of stocks and bonds
   - Total value of $500,000 explicitly stated
   - Single owner P3 (Robert Johnson) clearly identified
</reasoning>

<name>
[{"id": "P1", "firstname": "John", "lastname": "Smith"}, {"id": "P2", "firstname": "Jane", "lastname": "Doe"}, {"id": "P3", "firstname": "Robert", "lastname": "Johnson"}]
</name>

<asset>
[
  {
    "name": "Beach House",
    "category": "Real Estate",
    "value": 1200000,
    "owners": ["P1", "P2"],
    "valuesPerOwner": {
      "P1": 600000,
      "P2": 600000
    }
  },
  {
    "name": "Investment Portfolio",
    "category": "Financial",
    "value": 500000,
    "owners": ["P3"],
    "valuesPerOwner": {
      "P3": 500000
    }
  }
]
</asset>"""
                
            user_prompt = f"Extract all names of people and assets from the following text:\n\n{text}"
            
            # Call DeepSeek API - using synchronous call
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for more deterministic results
                stream=False
            )
            
            # Extract the response content
            result_text = response.choices[0].message.content
            
            # Parse the response to extract reasoning, names, and assets
            reasoning = ""
            names = []
            assets = []
            
            # Extract reasoning section
            reasoning_start = result_text.find("<reasoning>")
            reasoning_end = result_text.find("</reasoning>")
            if reasoning_start != -1 and reasoning_end != -1:
                reasoning = result_text[reasoning_start + len("<reasoning>"):reasoning_end].strip()
            
            # Extract names section
            names_start = result_text.find("<name>")
            names_end = result_text.find("</name>")
            if names_start != -1 and names_end != -1:
                names_text = result_text[names_start + len("<name>"):names_end].strip()
                try:
                    names = json.loads(names_text)
                except json.JSONDecodeError:
                    # If JSON parsing fails, try to extract names using string manipulation
                    print(f"Failed to parse JSON in <name> section: {names_text}")
                    # Try to extract firstname and lastname pairs
                    pattern = r'"firstname":\s*"([^"]+)",\s*"lastname":\s*"([^"]+)"'
                    matches = re.findall(pattern, names_text)
                    if matches:
                        names = [{"id": f"P{i+1}", "firstname": first, "lastname": last} for i, (first, last) in enumerate(matches)]
                    else:
                        names = []
            
            # Extract assets section
            assets_start = result_text.find("<asset>")
            assets_end = result_text.find("</asset>")
            if assets_start != -1 and assets_end != -1:
                assets_text = result_text[assets_start + len("<asset>"):assets_end].strip()
                try:
                    assets = json.loads(assets_text)
                except json.JSONDecodeError:
                    # If JSON parsing fails, log the error
                    print(f"Failed to parse JSON in <asset> section: {assets_text}")
                    assets = []
            
            # Return the extracted information
            return {
                "reasoning": reasoning,
                "names": names,
                "namesCount": len(names),
                "assets": assets,
                "assetsCount": len(assets)
            }
                
        except Exception as e:
            print(f"Error extracting information with DeepSeek: {str(e)}")
            return {
                "reasoning": f"Error occurred: {str(e)}",
                "names": [],
                "namesCount": 0,
                "assets": [],
                "assetsCount": 0
            }
    
    # Add your custom processing methods here later

