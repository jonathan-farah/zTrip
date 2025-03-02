import os 
import json  # Allows handling of JSON data, which is a common data format
from dotenv import load_dotenv  # Helps load environment variables from a .env file
from web3 import Web3  # Library to interact with Ethereum blockchain
from anthropic import Anthropic  # Library to use Claude AI model
import streamlit as st  # Framework to create web applications 
from pycoingecko import CoinGeckoAPI # Import the CoinGecko API library for cryptocurrency data
import time  

# Load environment variables from the .env file for security
load_dotenv()

# Initialize connection to ETH chain
w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_PROVIDER_URI")))

# Create an Ethereum account using the private key 
account = w3.eth.account.from_key(os.getenv("WALLET_PRIVATE_KEY"))

# Load the smart contract's ABI (Application Binary Interface) from a JSON file
# The ABI defines how to interact with functions on the smart contract
with open('abi/Prompt.json', 'r') as f: 
    contract_abi = json.load(f)  # Parse the JSON into a Python object

# Initialize the contract object with its address and ABI
contract_address = os.getenv("CONTRACT_ADDRESS")  # Get contract address from environment variables
contract = w3.eth.contract(address=contract_address, abi=contract_abi)  # Create contract object

anthropic_client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

def get_eth_price():
    """Get current ETH price and 24h change"""
    try:
        cg = CoinGeckoAPI() 
        eth_data = cg.get_price(ids='ethereum', vs_currencies='usd', include_24hr_change=True)
        price = eth_data['ethereum']['usd']
        change_24h = eth_data['ethereum']['usd_24h_change']
        return price, change_24h
    
    except Exception as error_message:  
        print(f"Error fetching ETH price: {str(error_message)}")
        return None, None

eth_price, eth_change = get_eth_price()
print(f"Debug - ETH Price: ${eth_price}, Change: {eth_change}%")

def get_defi_recommendation(user_input, risk_profile):
    """Get DeFi recommendations using Claude API"""
    eth_price, eth_change = get_eth_price()
    eth_info = ""
    
    if eth_price is not None and eth_change is not None: 
        eth_info = f"Current ETH price: ${eth_price:,.2f} with a 24h change of {eth_change:.2f}%.\n" 
        
    # Create the prompt for Claude AI
    prompt = f"""
    You are a DeFi assistant helping users optimize their yield strategies.
    {eth_info}
    User risk profile: {risk_profile}
    User request: {user_input} 
    
    Provide a detailed recommendation for the best DeFi strategy based on the request and risk profile.
    Include specific protocols, expected yields, and risk factors.
    
    IMPORTANT: If the user is asking about ETH prices or ETH-related strategies, use the current ETH price information provided above.
    """
    
  
    message = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20240620", 
        max_tokens=5000, 
        temperature=0.2,  
        system="You are an expert in DeFi protocols and yield optimization strategies with access to current ETH price data.", 
        messages=[
            {"role": "user", "content": prompt} 
        ]
    )

   
    final_str = "" 
    
    # Handle different possible response formats from Claude API
    if hasattr(message.content, 'items'):  # If content is a dictionary loop through dictionary items
        for _, value in message.content.items():  
            if isinstance(value, str): 
                final_str += value 
    elif isinstance(message.content, list):  # If content is a list loop through the list
        for item in message.content:  
            if hasattr(item, 'text'):  
                final_str += item.text  
    else: 
        final_str = str(message.content)  

    return final_str

# Define function to send a prompt to the blockchain AI Oracle
def send_to_blockchain(prompt_text, model_id=11):  # Default to Llama3 model_id (11)
    # Submit prompt to blockchain AI Oracle
    try: 
        # This calculates how much ETH is needed to pay for the transaction
        fee = contract.functions.estimateFee(model_id).call()
        
        # Build a transaction to call the calculateAIResult function on the smart contract
        tx = contract.functions.calculateAIResult(model_id, prompt_text).build_transaction({
            'from': account.address,  # Sender's address
            'gas': 3000000,  # Maximum gas units allowed
            'gasPrice': w3.eth.gas_price,  # Current gas price 
            'nonce': w3.eth.get_transaction_count(account.address),  # Transaction sequence number
            'value': fee  # Amount of ETH to send with the transaction
        })
        
        # Sign the transaction with the private key
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=os.getenv("WALLET_PRIVATE_KEY"))
        
        # Send the signed transaction to the blockchain
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction to be mined and included in a block
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        # Return the transaction hash
        return tx_hash.hex()
    except Exception as error_message:  
        # Show in UI
        st.error(f"Error submitting to blockchain: {str(error_message)}")
        
        return None

# Get the result from the blockchain after processing
def get_blockchain_result(model_id, prompt_text):
    try: 
        # This retrieves the AI-generated result for the given prompt
        result = contract.functions.getAIResult(model_id, prompt_text).call()
        return result
    
    except Exception as error1:  
        # Show in UI
        st.error(f"Error getting blockchain result: {str(error1)}")
        
        return "Result not available yet. The AI Oracle may still be processing your request."


# Streamlit UI section
# Display ETH price data
eth_price, eth_change = get_eth_price()  
if eth_price is not None and eth_change is not None: 
    price_col, change_col = st.columns(2)
    price_col.metric("ETH Price", f"${eth_price:,.2f}")
    change_col.metric("24h Change", f"{eth_change:.2f}%", f"{eth_change:.2f}%")
    
# Display the main title of the app
st.title("DeFi Assistant")

risk_profile = st.selectbox(
    "Select your risk profile:", 
    ["Conservative", "Moderate", "Aggressive"]  
)

user_input = st.text_area("What would you like help with today?",  "I want..." )

# Create a button
if st.button("Get Recommendations"): 
    # Show a spinner while generating recommendations
    with st.spinner("Generating recommendations with Claude..."):
        # Call the function to get recommendations from Claude
        claude_recommendation = get_defi_recommendation(user_input, risk_profile)
        
        # Display recommendation
        st.write("### Claude Recommendation")
        st.write(claude_recommendation)
    
    # Create two columns for blockchain interaction buttons
    blockchain_col1, blockchain_col2 = st.columns(2)
    
    with blockchain_col1:
        if st.button("Submit to Blockchain Oracle"): 
            # Format the prompt for the blockchain call
            blockchain_prompt = f"Analyze yield optimization for {user_input} with {risk_profile} risk profile"
            
            # Show a spinner while submitting to blockchain
            with st.spinner("Submitting to blockchain..."):
                # Call function to send prompt to blockchain
                tx_hash = send_to_blockchain(blockchain_prompt)
                
                if tx_hash:  # If submission was successful
                    # Store transaction hash in session state for later use
                    st.session_state['tx_hash'] = tx_hash
                    
                    # Show success message with transaction hash
                    st.success(f"Transaction submitted! Hash: {tx_hash}")
                    
                    # Show informational message about processing time
                    st.info("The blockchain AI Oracle will process your request. This may take some time.")
    
    # Second column contains the "Check Blockchain Result" button
    with blockchain_col2:
        # Only show and process this button if a transaction has been submitted
        if st.button("Check Blockchain Result") and 'tx_hash' in st.session_state:
            # Show a spinner while checking the result
            with st.spinner("Checking result..."):
                # Use the same prompt for consistency
                blockchain_prompt = f"Analyze yield optimization for {user_input} with {risk_profile} risk profile"
                
                # Call function to get result from blockchain
                result = get_blockchain_result(11, blockchain_prompt)  # Using Llama3 model_id (11)
                
                # Display a subheading for blockchain result
                st.write("### Blockchain Oracle Result")
                
                # Display the result text
                st.write(result)