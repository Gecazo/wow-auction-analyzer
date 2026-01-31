import re
import json
from datetime import datetime
from typing import Dict, Any

def parse_lua_file(filepath: str) -> Dict[str, Any]:
    """Parse the Auctionator.lua file and extract price database"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the AUCTIONATOR_PRICE_DATABASE section
    match = re.search(r'AUCTIONATOR_PRICE_DATABASE = ({.*?})\nAUCTIONATOR_LAST_SCAN_TIME', 
                     content, re.DOTALL)
    
    if not match:
        print("Could not find AUCTIONATOR_PRICE_DATABASE")
        return {}
    
    lua_data = match.group(1)
    
    # Parse the structure
    items = {}
    current_item = None
    current_realm = None
    
    # Find realm name
    realm_match = re.search(r'\["([^"]+)"\] = {', lua_data)
    if realm_match:
        current_realm = realm_match.group(1)
    
    # Parse line by line to capture all variations dynamically
    lines = lua_data.split('\n')
    current_item_name = None
    current_item_data = {}
    
    for line in lines:
        # Check if this is an item name
        item_name_match = re.match(r'\s*\["([^"]+)"\] = {', line)
        if item_name_match and line.count('[') == 1:
            # Save previous item if exists
            if current_item_name and current_item_data:
                items[current_item_name] = current_item_data.copy()
            
            current_item_name = item_name_match.group(1)
            current_item_data = {}
            continue
        
        # Extract data fields
        if current_item_name:
            # Check for lastScan
            scan_match = re.search(r'\["lastScan"\] = (\d+)', line)
            if scan_match:
                current_item_data['lastScan'] = int(scan_match.group(1))
            
            # Check for mr (market rate)
            mr_match = re.search(r'\["mr"\] = (\d+)', line)
            if mr_match:
                current_item_data['mr'] = int(mr_match.group(1))
            
            # Check for historical prices (H5553, H5554, etc.)
            hist_match = re.search(r'\["(H\d+)"\] = (\d+)', line)
            if hist_match:
                current_item_data[hist_match.group(1)] = int(hist_match.group(2))
            
            # Check for closing brace
            if line.strip() == '},':
                if current_item_data:
                    items[current_item_name] = current_item_data.copy()
                current_item_name = None
                current_item_data = {}
    
    return {
        'realm': current_realm,
        'items': items
    }

def convert_copper_to_gold(copper: int) -> str:
    """Convert copper to gold/silver/copper format"""
    gold = copper // 10000
    silver = (copper % 10000) // 100
    copper_remainder = copper % 100
    
    if gold > 0:
        return f"{gold}g {silver}s {copper_remainder}c"
    elif silver > 0:
        return f"{silver}s {copper_remainder}c"
    else:
        return f"{copper_remainder}c"

def main():
    print("Parsing Auctionator.lua...")
    data = parse_lua_file('Auctionator.lua')
    
    print(f"\nRealm: {data.get('realm', 'Unknown')}")
    print(f"Total items: {len(data['items'])}")
    
    # Export to JSON for the web viewer
    output = {
        'realm': data['realm'],
        'items': []
    }
    
    for item_name, item_data in data['items'].items():
        item_entry = {
            'name': item_name,
            'lastScan': item_data.get('lastScan', 0),
            'mr': item_data.get('mr', 0),
            'history': {}
        }
        
        # Extract all historical data dynamically (any H-prefixed keys)
        for key, value in item_data.items():
            if key.startswith('H') and key[1:].isdigit():
                item_entry['history'][key] = value
        
        output['items'].append(item_entry)
    
    # Save to JSON
    with open('price_data.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nData exported to price_data.json")
    
    # Show some sample items with price history
    print("\nSample items with price history:")
    count = 0
    for item_name, item_data in data['items'].items():
        hist_keys = [k for k in item_data.keys() if k.startswith('H')]
        if len(hist_keys) >= 2:  # Items with multiple price points
            print(f"\n{item_name}:")
            print(f"  Current: {convert_copper_to_gold(item_data.get('mr', 0))}")
            for hist_key in sorted(hist_keys):
                print(f"  {hist_key}: {convert_copper_to_gold(item_data[hist_key])}")
            count += 1
            if count >= 5:
                break

if __name__ == '__main__':
    main()
