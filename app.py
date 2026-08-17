import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import re
import os

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="AML QA Copilot",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ AML QA Copilot")
st.caption("Automated Quality Assurance & Risk Assessment for AML Investigation Reports")

# ---------------------------------------------------------
# Utility: PII Data Masking / Anonymization
# ---------------------------------------------------------
def anonymize_text(text: str) -> str:
    """Replaces sensitive Personal Identifiable Information (PII) with generic tags."""
    if not isinstance(text, str):
        return text
    
    # Mask Emails
    text = re.sub(r'[\w\.-]+@[\w\.-]+\.\w+', '[REDACTED_EMAIL]', text)
    # Mask Phone Numbers (Local and International formats)
    text = re.sub(r'\+?\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}', '[REDACTED_PHONE]', text)
    # Mask Account Numbers / Credit Cards (8+ contiguous digits)
    text = re.sub(r'\b\d{8,19}\b', '[REDACTED_ACCOUNT_NO]', text)
    
    return text

# ---------------------------------------------------------
# Sidebar Configuration
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Get API key from environment variable or sidebar input
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        api_key = st.text_input("Enter Gemini API Key:", type="password")
        
    st.divider()
    enable_masking = st.checkbox("🛡️ Enable Data Anonymization (PII Masking)", value=True, 
                                 help="Automatically redacts emails, phones, and account numbers before AI processing.")

# ---------------------------------------------------------
# Main Interface: File Upload
# ---------------------------------------------------------
st.subheader("📁 Upload AML Case Data")
uploaded_file = st.file_uploader("Upload Case File (JSON or Excel .xlsx)", type=["json", "xlsx"])

if uploaded_file:
    narrative_text = ""
    transactions_data = ""
    
    try:
        if uploaded_file.name.endswith(".json"):
            data = json.load(uploaded_file)
            narrative_text = str(data.get("narrative", ""))
            transactions_data = json.dumps(data.get("transactions", []), indent=2)
            
        elif uploaded_file.name.endswith(".xlsx"):
            xls = pd.ExcelFile(uploaded_file)
            # Try reading 'Narrative' sheet or first sheet
            if "Narrative" in xls.sheet_names:
                df_narrative = pd.read_excel(xls, sheet_name="Narrative")
                narrative_text = " ".join(df_narrative.astype(str).values.flatten())
            else:
                df_first = pd.read_excel(xls, sheet_name=0)
                narrative_text = " ".join(df_first.astype(str).values.flatten())
                
            # Try reading 'Transactions' sheet
            if "Transactions" in xls.sheet_names:
                df_tx = pd.read_excel(xls, sheet_name="Transactions")
                transactions_data = df_tx.to_json(orient="records", indent=2)
            else:
                transactions_data = "[]"
                
        # Apply Data Masking if enabled
        if enable_masking:
            narrative_text = anonymize_text(narrative_text)
            transactions_data = anonymize_text(transactions_data)
            st.success("✅ PII Masking applied successfully! Sensitive data redacted.")
        
        # Display preview tabs
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Case Narrative Preview:**")
            st.text_area("Narrative", narrative_text, height=150, disabled=True)
        with col2:
            st.markdown("**Transactions Preview:**")
            st.text_area("Transactions", transactions_data, height=150, disabled=True)

        # ---------------------------------------------------------
        # AI Audit Execution
        # ---------------------------------------------------------
        st.divider()
        if st.button("🚀 Run AML QA Audit", type="primary"):
            if not api_key:
                st.error("Please provide a Gemini API Key in the sidebar or environment variable.")
            else:
                with st.spinner("Analyzing case narrative against transactions for compliance errors..."):
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    
                    prompt = f"""
                    You are an expert Anti-Money Laundering (AML) Quality Assurance Auditor.
                    Analyze the following AML Investigation Report Narrative and matched Transactions Data.
                    
                    Narrative:
                    {narrative_text}
                    
                    Transactions:
                    {transactions_data}
                    
                    Perform a rigorous QA audit and return your response in structured Markdown covering:
                    1. **Overall QA Score (1-10)**
                    2. **Summary of Audit Findings**
                    3. **Discrepancies & Missed Red Flags** (Compare narrative claims vs actual transaction data)
                    4. **Risk Assessment & Key Findings**
                    5. **Actionable Recommendations for Investigator**
                    """
                    
                    response = model.generate_content(prompt)
                    st.subheader("📋 Audit Report Results")
                    st.markdown(response.text)
                    
    except Exception as e:
        st.error(f"Error processing file: {e}")