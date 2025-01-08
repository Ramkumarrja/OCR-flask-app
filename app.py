from flask import Flask, request, jsonify
import openai
import os
import base64
import json
from dotenv import load_dotenv
from flask_cors import CORS

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Initialize Flask app
app = Flask(__name__)

CORS(app)

# Directory to save extracted data
DATA_FOLDER = '/tmp/data'  # Update to use the writable /tmp directory
os.makedirs(DATA_FOLDER, exist_ok=True)

# Function to encode the image to base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# Function to save extracted data as JSON
def save_extracted_data_as_json(data, file_name):
    json_file_name = f"{os.path.splitext(file_name)[0]}.json"  # Change extension to .json
    json_file_path = os.path.join(DATA_FOLDER, json_file_name)
    with open(json_file_path, 'w') as json_file:
        json.dump(data, json_file, indent=4)
    return json_file_name

# API route to upload an image and extract text
@app.route("/api/extract", methods=["POST"])
def extract_text():
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    uploaded_image = request.files["image"]
    if uploaded_image.filename == "":
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded image temporarily
    image_path = os.path.join(DATA_FOLDER, uploaded_image.filename)
    uploaded_image.save(image_path)

    # Prepare the prompt
    prompt = """What's in the image? Provide the text in a structured format covering:
    - Name
    - Father's Name
    - Date of Birth
    - Card Number
    """

    # Encode image to base64
    base64_image = encode_image(image_path)

    # Request to OpenAI API for text extraction
    try:
        chat_completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ]
        )
        extracted_text = chat_completion.choices[0].message.content

        # Parse and clean the extracted data
        extracted_data = {}
        lines = extracted_text.split("\n")
        for line in lines:
            line = line.replace("**", "").strip()
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.replace("-", "").strip()
                value = value.strip()
                extracted_data[key] = value

        # Save extracted data as JSON
        json_file_name = save_extracted_data_as_json(extracted_data, uploaded_image.filename)

        return jsonify({
            "message": "Text extracted successfully",
            "extracted_data": extracted_data,
            "json_file_name": json_file_name
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/", methods=["GET"])
def testing():
    return jsonify({"message": "server running "})

# Run Flask app
if __name__ == "__main__":
    app.run(debug=True)
