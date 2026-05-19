import json
import os

config_file = "config.json"
if os.path.exists(config_file):
    with open(config_file, 'r') as f:
        config = json.load(f)
    config["company_name"] = "VICTOR'S SUPER MARKET"
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=4)
    print("✅ Company name updated to VICTOR'S SUPER MARKET")
else:
    print("config.json not found. Run the main program first to create it.")