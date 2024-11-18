import json

from flask import Flask, request, jsonify
import requests
import fitz  # PyMuPDF

app = Flask(__name__)

# Replace these with your Azure Document Intelligence endpoint and API key
AZURE_ENDPOINT = "https://docintprudhvi.cognitiveservices.azure.com/"
API_KEY = "C5MpFIwSPmkCZcWhOc65a753bQmoCtNeF9m8TfTD8IhXTAzZ3oi7JQQJ99AKACYeBjFXJ3w3AAALACOGfgpD"

poll_url_list=[]
def send_to_azure(page_data):
    try:
        url = f"{AZURE_ENDPOINT}documentintelligence/documentModels/prebuilt-layout:analyze?api-version=2024-02-29-preview&features=formulas"
        headers = {
            "Ocp-Apim-Subscription-Key": API_KEY,
            "Content-Type": "application/pdf"
        }
        response = requests.post(url, headers=headers, data=page_data)
        response.raise_for_status()  # Will raise an exception for HTTP errors

        # Check for 202 Accepted response, indicating asynchronous processing add it the poll Url List
        if response.status_code == 202:
            poll_url = response.headers.get("Operation-Location")
            return {"poll_url": poll_url}
        else:
            return response.json()  # Directly return JSON response if processing is synchronous
    except requests.exceptions.RequestException as e:
        return {"error": "Failed to connect to Azure Document Intelligence", "details": str(e)}

def poll_for_result(poll_url_list):
    headers = {
        "Ocp-Apim-Subscription-Key": API_KEY
    }
    results=[]
    page_num=0
    for poll_url in poll_url_list:
        page_num=page_num+1
        poll_result = requests.get(poll_url, headers=headers)
        results_json = json.dumps(poll_result.content.decode("utf-8"), indent=4)
        results.append({"page_num": page_num, "result": results_json})

    return  results

@app.route('/analyze-document', methods=['POST'])
def analyze_document():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        # Load the PDF with PyMuPDF
        pdf_document = fitz.open(stream=file.read(), filetype="pdf")
    except Exception as e:
        return jsonify({"error": "Failed to read PDF", "details": str(e)}), 400

    results = []
    for page_num in range(pdf_document.page_count):
        try:
            # Extract each page as a single-page PDF
            single_page_pdf = fitz.open()  # Create a new blank PDF
            single_page_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)

            # Convert the single page to bytes for sending
            page_data = single_page_pdf.write()  # Get the binary content of the single-page PDF
            single_page_pdf.close()

            # Send the single page to Azure Document Intelligence
            response = send_to_azure(page_data)

            # Check if we received a polling URL for asynchronous processing
            if isinstance(response, dict) and "poll_url" in response:
                poll_url_list.append(response["poll_url"])

            elif "error" in response:
                # If there's an error in response
                results.append({"error": response["error"], "page_num": page_num, "details": response.get("details")})
            else:
                # Synchronous response, add directly to results
                results.append({"page_num": page_num, "result": response})

        except Exception as e:
            # Handle any unexpected errors during page processing
            results.append({"error": "Error processing page", "page_num": page_num, "details": str(e)})

    pdf_document.close()
    return jsonify({"result": poll_for_result(poll_url_list)}), 200

if __name__ == '__main__':
    app.run(debug=True)
