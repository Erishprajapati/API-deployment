import re

def extract_mentions(content : str):
    return re.findall(r"@(\w+)", content)