import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

from flask import Flask, request, jsonify, send_from_directory
from src.display.load_and_visualize import load_all_esg_data, plot_company_all_three_categories, compare_companies_metrics

import io
import base64
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

app = Flask(__name__, static_folder="static")

df_all = load_all_esg_data()

# Serve the frontend
@app.route("/", methods=["GET"])
def index():
    # Serve index.html from the current directory (src/display/)
    return send_from_directory(os.path.dirname(__file__), "index.html")

@app.route('/plot-company', methods=["POST"])
def plot_company_api():
    try:
        data = request.get_json()
        company_name = data.get("company_name")

        if not company_name:
            return jsonify({"error": "No company name provided"}), 400

        plt.clf()
        plot_company_all_three_categories(df_all, company_name)

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')

        return jsonify({"image": img_base64})

    except Exception as e:
        print(f"Error in /plot-company: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/compare-companies', methods=["POST"])
def compare_companies_api():
    try:
        data = request.get_json()
        company_names = data.get("company_names")
        indicators = data.get("indicators")

        if not company_names or not indicators:
            return jsonify({"error": "Company names or indicators missing"}), 400

        plt.clf()
        compare_companies_metrics(df_all, company_names, indicators)

        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format="png", bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.read()).decode('utf-8')

        return jsonify({"image": img_base64})

    except Exception as e:
        print(f"Error in /compare-companies: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5550, debug=True)
