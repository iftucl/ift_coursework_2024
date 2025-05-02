from modules.config.env_loader import deepseek_client
import tiktoken

# Define maximum number of tokens allowed per DeepSeek API request
MAX_TOKENS_PER_REQUEST = 50000

def count_tokens(text: str) -> int:
    """
    Count the number of tokens in the given text using the tiktoken library.

    Args:
        text (str): The input text to count tokens for.

    Returns:
        int: The number of tokens in the text.
    """
    encoder = tiktoken.encoding_for_model("gpt-4")  # Adjust encoder if using a different model
    return len(encoder.encode(text))

def query_deepseek(text):
    """
    Send a query to DeepSeek to extract specific sustainability indicators from the text.

    The prompt requests extraction of specific indicators and ensures JSON format in the response.

    Args:
        text (str): The input text to analyze and extract indicators from.

    Returns:
        str: The JSON-formatted string returned by DeepSeek.
    """
    prompt = (
        "Extract the following indicators ALWAYS, even if not reported or marked as N/A: "
        "Scope 1 Emissions, Scope 2 Emissions, Scope 3 Emissions, Total Water Withdrawal, Total Water Consumption, Total Energy Consumption, Renewable Energy Consumption, Total Waste Generated, Hazardous Waste. "
        "For each, extract: value, unit, and the reporting year. "
        "If the indicator is not reported, use value=null and unit=null. "
        "ALSO extract overall reporting year if mentioned in the document (like '2023 Sustainability Report'). "
        "Return JSON only. Example format: { 'Scope 1 Emissions': {'value': 32400, 'unit': 'metric tons CO2e', 'year': 2023 }, ... }"
        "\n\nText to analyze:\n"
        f"{text}\n"
        "\nPlease reply ONLY in JSON format."
    )

    response = deepseek_client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": "You are a helpful assistant"},
                  {"role": "user", "content": prompt}],
        stream=False
    )
    return response.choices[0].message.content

def query_deepseek_dynamic(full_text, pages_text):
    """
    Dynamically split text and send to DeepSeek API based on token limits.

    If full text is within token limits, process as a single chunk. Otherwise, split into smaller chunks.
    Skips chunks that are too small or too large (for now).

    Args:
        full_text (str): Full extracted text from the document.
        pages_text (list): List of text for each page, used for chunking.

    Returns:
        list: A list of JSON-formatted strings returned by DeepSeek for each processed chunk.
    """
    token_count = count_tokens(full_text)

    if token_count <= MAX_TOKENS_PER_REQUEST:
        print("Processing full text as single chunk...")
        return [query_deepseek(full_text)]

    results = []
    chunk_size = 5  # Number of pages per chunk
    total_pages = len(pages_text)
    chunks = [pages_text[i:i + chunk_size] for i in range(0, total_pages, chunk_size)]
    total_chunks = len(chunks)

    # Process each chunk individually
    for idx, chunk in enumerate(chunks, start=1):
        chunk_text = "\n".join(chunk)

        if len(chunk_text.strip()) < 100:
            print(f"Skipping empty/small chunk {idx}/{total_chunks}")
            continue

        if count_tokens(chunk_text) > MAX_TOKENS_PER_REQUEST:
            print(f"Chunk {idx} too large, further splitting is needed but skipped for now.")
            continue

        print(f"Processing chunk {idx}/{total_chunks}... Remaining chunks: {total_chunks - idx}")
        result = query_deepseek(chunk_text)
        results.append(result)

    return results