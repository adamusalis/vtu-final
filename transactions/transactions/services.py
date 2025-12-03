import requests

import requests
import logging
from django.conf import settings

# Set up a logger so we can see what's happening in the terminal/logs
logger = logging.getLogger(__name__)

class RealVTUVendor:
    """
    Integrates with the Clubkonnect VTU API.
    Documentation: (You would put the link to their docs here)
    """

    # Map our internal network names to the vendor's specific network IDs.
    # IMPORTANT: You must check your vendor's docs for the correct IDs!
    # These are example IDs for Clubkonnect.
    NETWORK_MAPPING = {
        'MTN': '01',
        'GLO': '02',
        'AIRTEL': '03',
        '9MOBILE': '04',
    }

    def __init__(self):
        # Load credentials securely from settings.py (which got them from .env)
        self.user_id = settings.VTU_API_USERID
        self.api_key = settings.VTU_API_KEY
        self.base_url = settings.VTU_BASE_URL

        # Basic check to ensure keys are set
        if not self.user_id or not self.api_key or not self.base_url:
            logger.error("VTU Vendor credentials not configured in settings.")
            raise Exception("Vendor credentials missing.")

    def purchase_airtime(self, network, phone, amount, ref_id):
        """
        Sends the actual HTTP request to the vendor to buy airtime.
        """
        # 1. Get the correct vendor network ID
        vendor_network_id = self.NETWORK_MAPPING.get(network.upper())
        if not vendor_network_id:
            logger.error(f"Unsupported network attempted: {network}")
            return {
                "status": "failed",
                "message": f"Unsupported network: {network}",
                "raw_response": {}
            }

        # 2. Prepare the parameters for the API call
        # Clubkonnect uses a GET request with query parameters.
        params = {
            'UserID': self.user_id,
            'APIKey': self.api_key,
            'MobileNo': phone,
            # Ensure amount is an integer (vendors usually don't like decimals)
            'Amount': int(float(amount)),
            'NetworkID': vendor_network_id,
            'RequestID': ref_id, # Crucial for preventing double-spending!
            'callBackURL': '' # Optional: leave blank for now
        }

        # Construct the full endpoint URL (e.g., .../GetCredit.asp)
        # Double-check the exact endpoint name in your vendor's docs.
        endpoint = f"{self.base_url.rstrip('/')}/GetCredit.asp"

        logger.info(f"Calling Vendor API: {endpoint} with params (excluding keys): MobileNo={phone}, Amount={amount}, Ref={ref_id}")

        try:
            # 3. FIRE THE REQUEST! 🚀
            # We use a 30-second timeout so our server doesn't hang forever if theirs is down.
            response = requests.get(endpoint, params=params, timeout=30)
           
            # Raise an exception if the HTTP status is bad (e.g., 404, 500)
            response.raise_for_status()
           
            # 4. Parse the response
            # Clubkonnect returns JSON. We need to convert it to a Python dictionary.
            response_data = response.json()
            logger.info(f"Vendor Response Raw: {response.text}")

            # 5. Interpret the result based on Vendor's rules
            # Clubkonnect convention: "status" key indicates outcome.
            # '100' usually means Success. Everything else is likely a failure or pending.
           
            vendor_status_code = response_data.get('status')

            if vendor_status_code == '100':
                # --- SUCCESS ---
                # They usually send back their own reference ID (e.g., 'orderid')
                vendor_ref = response_data.get('orderid', 'N/A')
                return {
                    "status": "success",
                    "message": "Transaction Successful",
                    "vendor_reference": vendor_ref,
                    "raw_response": response_data
                }
           
            elif vendor_status_code == '200':
                 # --- COMMON FAILURE (e.g. Bad Request, Insufficient Balance) ---
                 error_msg = response_data.get('msg', 'Transaction Failed at vendor')
                 return {
                    "status": "failed",
                    "message": error_msg,
                    "vendor_reference": None,
                    "raw_response": response_data
                }
           
            else:
                # --- UNKNOWN / PENDING STATE ---
                # If we get a weird status code, it's safer to mark it failed and refund
                # than to assume it worked.
                logger.warning(f"Unknown vendor status code: {vendor_status_code}")
                return {
                    "status": "failed",
                    "message": f"Vendor returned unknown status: {vendor_status_code}",
                    "vendor_reference": None,
                    "raw_response": response_data
                }

        except requests.exceptions.RequestException as e:
            # This handles network errors (DNS failure, connection timeout, etc.)
            logger.error(f"HTTP Request failed: {e}")
            return {
                "status": "failed",
                "message": "Unable to connect to network provider. Please try again later.",
                "vendor_reference": None,
                "raw_response": {"error": str(e)}
            }
        except ValueError as e:
             # This handles cases where the vendor sends back invalid JSON
            logger.error(f"Failed to parse vendor JSON response: {e}. Raw body: {response.text}")
            return {
                "status": "failed",
                "message": "Bad response from network provider.",
                "vendor_reference": None,
                "raw_response": {"error": "Invalid JSON", "body": response.text}
            }