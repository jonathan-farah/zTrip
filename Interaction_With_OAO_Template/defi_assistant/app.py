# app.py
import os
import json
from dotenv import load_dotenv
from web3 import Web3
from anthropic import Anthropic
import streamlit as st
import time

# Load environment variables
load_dotenv()

# Initialize Web3
w3 = Web3(Web3.HTTPProvider(os.getenv("WEB3_PROVIDER_URI")))
account = w3.eth.account.from_key(os.getenv("WALLET_PRIVATE_KEY"))

# Load contract ABI 
with open('abi/Prompt.json', 'r') as f:
    contract_abi = json.load(f)

# Initialize contract
contract_address = os.getenv("CONTRACT_ADDRESS")
contract = w3.eth.contract(address=contract_address, abi=contract_abi)

# Initialize Claude API client
anthropic_client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

def get_eth_price():
    """Get current ETH price and 24h change"""
    try:
        # You'll need to import the CoinGecko API
        from pycoingecko import CoinGeckoAPI
        cg = CoinGeckoAPI()
        
        eth_data = cg.get_price(ids='ethereum', vs_currencies='usd', include_24hr_change=True)
        price = eth_data['ethereum']['usd']
        change_24h = eth_data['ethereum']['usd_24h_change']
        return price, change_24h
    except Exception as e:
        print(f"Error fetching ETH price: {str(e)}")
        return None, None
    
eth_price, eth_change = get_eth_price()
print(f"Debug - ETH Price: ${eth_price}, Change: {eth_change}%")

def get_defi_recommendation(user_input, risk_profile):
    """Get DeFi recommendations using Claude API"""
    prompt = f"""
    You are a DeFi assistant helping users optimize their yield strategies.
    User risk profile: {risk_profile}
    User request: {user_input} 
    Provide a detailed recommendation for the best DeFi strategy based on the request and risk profile.
    Include specific protocols, expected yields, and risk factors."""
    
    message = anthropic_client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=1000,
        temperature=0.2,
        system="You are an expert in DeFi protocols and yield optimization strategies.",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    final_str = ""
    if hasattr(message.content, 'items'):  # If content is a dictionary
        for _, value in message.content.items():
            if isinstance(value, str):
                final_str += value
    elif isinstance(message.content, list):  # If content is a list
        for item in message.content:
            if hasattr(item, 'text'):
                final_str += item.text
    else:  # If content is already a string or something else
        final_str = str(message.content)
    
    return final_str

def send_to_blockchain(prompt_text, model_id=11):  # Default to Llama3 model_id
    """Submit prompt to blockchain AI Oracle"""
    try:
        # Estimate the fee required for the AI request
        fee = contract.functions.estimateFee(model_id).call()
        
        # Submit the transaction to the blockchain
        tx = contract.functions.calculateAIResult(model_id, prompt_text).build_transaction({
            'from': account.address,
            'gas': 3000000,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'value': fee
        })
        
        # Sign and send transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=os.getenv("WALLET_PRIVATE_KEY"))
        tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)
        
        # Wait for transaction receipt
        tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        
        return tx_hash.hex()
    except Exception as e:
        st.error(f"Error submitting to blockchain: {str(e)}")
        return None

def get_blockchain_result(model_id, prompt_text):
    """Get the result from the blockchain after processing"""
    try:
        # This function will retrieve the result from the blockchain
        result = contract.functions.getAIResult(model_id, prompt_text).call()
        return result
    except Exception as e:
        st.error(f"Error getting blockchain result: {str(e)}")
        return "Result not available yet. The AI Oracle may still be processing your request."

# Streamlit UI
st.title("DeFi Assistant")

risk_profile = st.selectbox(
    "Select your risk profile:",
    ["Conservative", "Moderate", "Aggressive"]
)

user_input = st.text_area("What would you like help with today?", 
                        "I want to optimize my yield on 10,000 USDC")

if st.button("Get Recommendations"):
    with st.spinner("Generating recommendations with Claude..."):
        claude_recommendation = get_defi_recommendation(user_input, risk_profile)
        st.write("### Claude Recommendation")
        st.write(claude_recommendation)
    
    blockchain_col1, blockchain_col2 = st.columns(2)
    
    with blockchain_col1:
        if st.button("Submit to Blockchain Oracle"):
            # Format the prompt for the blockchain call
            blockchain_prompt = f"Analyze yield optimization for {user_input} with {risk_profile} risk profile"
            
            with st.spinner("Submitting to blockchain..."):
                tx_hash = send_to_blockchain(blockchain_prompt)
                if tx_hash:
                    st.session_state['tx_hash'] = tx_hash
                    st.success(f"Transaction submitted! Hash: {tx_hash}")
                    st.info("The blockchain AI Oracle will process your request. This may take some time.")
    
    with blockchain_col2:
        if st.button("Check Blockchain Result") and 'tx_hash' in st.session_state:
            with st.spinner("Checking result..."):
                blockchain_prompt = f"Analyze yield optimization for {user_input} with {risk_profile} risk profile"
                result = get_blockchain_result(11, blockchain_prompt)  # Using Llama3 model_id
                st.write("### Blockchain Oracle Result")
                st.write(result)