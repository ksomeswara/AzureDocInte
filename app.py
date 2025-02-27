import json
import requests
import os
import zipfile
import fitz  # PyMuPDF
from flask import Flask, request, jsonify
from OpenAIChat import OpenAIChat  # Assuming OpenAIChat is defined in OpenAIChat.py

app = Flask(__name__)

# Replace these with your Azure Document Intelligence endpoint and API key
AZURE_ENDPOINT = "https://docintprudhvi.cognitiveservices.azure.com/"

chat = OpenAIChat()
model = "gpt-4o-mini"
messages = [
    {"role": "system", "content": "You are a Grader for a Subject Called Rader Signal Processing .You will be Given Solution LaTeX and Students Submission LaTex and Scoring Criteria"},
    {"role": "user", "content": "You will be Given Solution LaTeX and Students Submission LaTex and Scoring Criteria."}
]
result = chat.generate_completion(model, messages)
print("Generated Completion:")
print(result)

poll_url_list=[]

UPLOAD_FOLDER = '/tmp/Submissions'  # Change to the directory you want on the VM
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



@app.route('/testServer', methods=['get'])
def test_server():
    return  {"Status": "Active"},200
@app.route('/uploadSubmissions', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    if not file.filename.endswith('.zip'):
        return jsonify({"error": "Only .zip files are allowed"}), 400
    try:
        file.save(os.path.join(UPLOAD_FOLDER, file.filename))
        return jsonify({"message": "File uploaded successfully"}), 200
    except Exception as e:
        return jsonify({"error": "Failed to save file", "details": str(e)}), 500
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
@app.route('/process-folder', methods=['POST'])
def process_folder():
    # Expected JSON payload containing the zip file location
    data = request.json
    if 'zip_path' not in data:
        return jsonify({"error": "No zip_path provided in the request"}), 400
    zip_path = data['zip_path']
    # Ensure the zip file exists
    if not os.path.exists(zip_path):
        return jsonify({"error": "Zip file not found at specified location"}), 400
    # Define a folder to extract the zip
    extract_folder = os.path.join(os.path.dirname(zip_path), "extracted_files")
    os.makedirs(extract_folder, exist_ok=True)
    try:
        # Unzip the file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
    except Exception as e:
        return jsonify({"error": "Failed to unzip file", "details": str(e)}), 400
    results = []
    for root, _, files in os.walk(extract_folder):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            # Ensure we only process PDFs or images
            if not (file_name.lower().endswith('.pdf') or file_name.lower().endswith(('.png', '.jpg', '.jpeg'))):
                continue
            try:
                # Extract the student ID from the filename
                student_id = file_name.split('-')[0].strip()
                if file_name.lower().endswith('.pdf'):
                    # Process PDF
                    pdf_document = fitz.open(file_path)
                    for page_num in range(pdf_document.page_count):
                        try:
                            single_page_pdf = fitz.open()
                            single_page_pdf.insert_pdf(pdf_document, from_page=page_num, to_page=page_num)
                            page_data = single_page_pdf.write()  # Binary content of single-page PDF
                            single_page_pdf.close()

                            # Send the single page to Azure Document Intelligence (placeholder function)
                            response = send_to_azure(page_data)

                            # Check the response and collect results
                            if isinstance(response, dict) and "poll_url" in response:
                                # Add poll URL to results if async
                                results.append({"student_id": student_id, "poll_url": response["poll_url"], "page_num": page_num})
                            elif "error" in response:
                                results.append({"error": response["error"], "student_id": student_id, "page_num": page_num})
                            else:
                                # Direct response
                                results.append({"student_id": student_id, "page_num": page_num, "result": response})
                        except Exception as e:
                            results.append({"error": "Error processing PDF page", "student_id": student_id, "page_num": page_num, "details": str(e)})
                    pdf_document.close()
                else:
                    # Process Images
                    with open(file_path, 'rb') as img_file:
                        img_data = img_file.read()
                        response = send_to_azure(img_data)
                        if isinstance(response, dict) and "poll_url" in response:
                            results.append({"student_id": student_id, "poll_url": response["poll_url"]})
                        elif "error" in response:
                            results.append({"error": response["error"], "student_id": student_id})
                        else:
                            results.append({"student_id": student_id, "result": response})
            except Exception as e:
                results.append({"error": "Error processing file", "file_name": file_name, "details": str(e)})
    return jsonify({"results": results}), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)

