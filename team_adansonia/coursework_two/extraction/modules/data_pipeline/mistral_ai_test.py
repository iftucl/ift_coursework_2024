"""
🌿 ESG Summarizer Powered by Mistral AI 🌍
-----------------------------------------
Leverage the capabilities of Mistral AI's open-source models to extract and summarize sustainability goals from ESG reports.

🔓 Open-source models: Mistral 7B, Mixtral 8x7B
🧠 Fine-tuned for ESG content summarization
💼 Ideal for analysts, researchers, and sustainability teams

GitHub: https://github.com/mistralai
"""
import mistral_ai
from mistral_ai import MistralModel

# Example parsed ESG content
parsed_esg_report = """
The company is committed to achieving net-zero carbon emissions by 2040. 
It plans to reduce water usage by 30% in all operations by 2030 and 
increase recycled materials in packaging to 75% by 2027. Additionally, 
diversity in leadership roles is targeted to reach 50% by 2026.
"""

# Initialize the Mistral AI model
model = MistralModel(model_name="mistral-7b")  # or "mixtral-8x7b"

# Generate a sustainability goal summary
summary = model.summarize(parsed_esg_report)

print("📋 Sustainability Goals Summary:")
print(summary)
