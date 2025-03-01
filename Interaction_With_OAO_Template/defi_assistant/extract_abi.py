# extract_abi.py
import json
import os

# Create abi directory if it doesn't exist
os.makedirs('abi', exist_ok=True)

# Load the compiled contract artifact
try:
    with open('../out/Prompt.sol/Prompt.json', 'r') as f:
        contract_data = json.load(f)

    # Extract and save just the ABI
    with open('abi/Prompt.json', 'w') as f:
        json.dump(contract_data['abi'], f, indent=2)

    print("ABI extracted and saved to abi/Prompt.json")
except FileNotFoundError:
    print("Error: Compiled contract file not found. Make sure you've compiled the contract.")
    print("Try running: forge build")
except Exception as e:
    print(f"Error extracting ABI: {str(e)}")