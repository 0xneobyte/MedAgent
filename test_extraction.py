import re
import datetime

def test_name_extraction():
    """Test name extraction with regex patterns"""
    test_names = [
        "My name is John Smith",
        "I'm Alex Muske",
        "This is Sarah Johnson",
        "Jane Doe is my name",
        "Robert",
        "Alex Benjamin"
    ]
    
    name_patterns = [
        # Explicit statements with name capture
        r'my name is\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})',
        r'I am\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})',
        r'I\'m\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})',
        r'call me\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})',
        r'it\'s\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})',
        r'this is\s+([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})',
        
        # Name followed by statement
        r'([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})(?:\s+(?:here|speaking|is my name))',
        
        # Capitalized names with 1-4 parts (first, middle, last names)
        r'([A-Z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})',
        
        # Names that might start with lowercase (user didn't capitalize)
        r'([A-Za-z][a-z]+(?:\s+[A-Za-z][a-z\']+){0,3})'
    ]
    
    print("Testing name extraction:")
    for test in test_names:
        extracted = None
        for pattern in name_patterns:
            match = re.search(pattern, test, re.IGNORECASE)
            if match:
                extracted = match.group(1).strip()
                if len(extracted.split()) >= 2 or len(extracted) > 3:
                    break
        
        print(f"Input: '{test}' -> Extracted: '{extracted}'")

def test_phone_extraction():
    """Test phone extraction with regex patterns"""
    test_phones = [
        "My phone number is 123-456-7890",
        "Call me at (077) 598-2859",
        "You can reach me at +44 7911 123456",
        "07759828590",
        "Phone: 555.123.4567"
    ]
    
    print("\nTesting phone extraction:")
    for test in test_phones:
        # Try special pattern for parentheses format first
        parentheses_pattern = r'\(\s*(\d{3})\s*\)\s*[-.\s]?\s*(\d{3})\s*[-.\s]?\s*(\d{4})'
        match = re.search(parentheses_pattern, test)
        if match:
            area_code = match.group(1)
            prefix = match.group(2)
            suffix = match.group(3)
            extracted = f"{area_code}-{prefix}-{suffix}"
            print(f"Input: '{test}' -> Extracted: '{extracted}'")
            continue
            
        # Try other patterns
        phone_patterns = [
            # US/North American formats
            r'\b(\d{3})[-.\s]?(\d{3})[-.\s]?(\d{4})\b',  # 123-456-7890, 123.456.7890, 123 456 7890
            
            # International formats
            r'\b(\+\d{1,3})[-.\s]?(\d{1,4})[-.\s]?(\d{1,4})[-.\s]?(\d{1,9})\b',  # +1-123-456-7890, +44 7911 123456
            r'\b(\d{2,3})[-.\s]?(\d{2,4})[-.\s]?(\d{2,4})[-.\s]?(\d{2,4})\b',  # 077-5982859
            
            # Simple digit sequences that look like phone numbers (must be at least 8 digits)
            r'\b(\d{8,15})\b',  # 1234567890, 07759828590
            
            # Formats with descriptive text
            r'phone(?:[-.\s]?(?:number)?[-.\s]?(?:is)?)[-.\s:]*([+\d][-.,()\s\d]{7,25})',  # phone: 123-456-7890
            r'number(?:[-.\s]?(?:is)?)[-.\s:]*([+\d][-.,()\s\d]{7,25})',  # number: 123-456-7890
            r'call(?:[-.\s]?(?:me)?)[-.\s:]*(?:at)?[-.\s:]*([+\d][-.,()\s\d]{7,25})'  # call me at 123-456-7890
        ]
        
        extracted = None
        for pattern in phone_patterns:
            if '-' in pattern and pattern.count('(') == 3:  # Pattern with multiple capture groups for formatting
                match = re.search(pattern, test)
                if match:
                    if pattern.startswith(r'\b(\d{3})[-.\s]?(\d{3})'):  # US format
                        area_code = match.group(1)
                        prefix = match.group(2)
                        suffix = match.group(3)
                        extracted = f"{area_code}-{prefix}-{suffix}"
                    elif pattern.startswith(r'\b(\+\d{1,3})'):  # International format
                        country = match.group(1)
                        parts = [match.group(i) for i in range(2, min(5, match.lastindex + 1))]
                        extracted = f"{country}-{'-'.join(parts)}"
                    elif pattern.startswith(r'\b(\d{2,3})[-.\s]?(\d{2,4})'):  # UK format
                        parts = [match.group(i) for i in range(1, min(5, match.lastindex + 1))]
                        extracted = '-'.join(parts)
                    break
            else:
                matches = re.findall(pattern, test)
                if matches:
                    if isinstance(matches[0], str):
                        longest_match = max(matches, key=len)
                        if longest_match.startswith('+'):
                            phone = '+' + re.sub(r'\D', '', longest_match[1:])
                        else:
                            phone = re.sub(r'\D', '', longest_match)
                        
                        if 7 <= len(phone) <= 15 or (phone.startswith('+') and 8 <= len(phone) <= 16):
                            # Format the phone number nicely based on its length and starting digits
                            if len(phone) == 10 and not phone.startswith('+'):
                                formatted_phone = f"{phone[:3]}-{phone[3:6]}-{phone[6:]}"
                            elif len(phone) == 11 and phone.startswith('1'):
                                formatted_phone = f"{phone[:1]}-{phone[1:4]}-{phone[4:7]}-{phone[7:]}"
                            elif len(phone) in [9, 10, 11] and (phone.startswith('07') or phone.startswith('447')):
                                # UK mobile format
                                if phone.startswith('07'):
                                    formatted_phone = f"0{phone[1:3]}-{phone[3:7]}-{phone[7:]}"
                                else:  # 447...
                                    formatted_phone = f"+44-{phone[2:5]}-{phone[5:8]}-{phone[8:]}"
                            else:
                                # Just add hyphens for readability
                                parts = [phone[i:i+3] for i in range(0, len(phone), 3)]
                                formatted_phone = "-".join(parts)
                            
                            extracted = formatted_phone
                            break
        
        print(f"Input: '{test}' -> Extracted: '{extracted}'")

def test_birthdate_extraction():
    """Test birthdate extraction with regex patterns"""
    test_birthdates = [
        "I was born on 1980-01-15",
        "My birth date is January 15, 1980",
        "DOB: 01/15/1980",
        "15th of January, 1980",
        "15-01-1980",
        "2005-11-03"
    ]
    
    month_to_num = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12'
    }
    
    date_patterns = [
        # YYYY-MM-DD: ISO format
        r'\b(19\d{2}|20\d{2})[-/\.](0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12][0-9]|3[01])\b',
        
        # MM-DD-YYYY: US format
        r'\b(0?[1-9]|1[0-2])[-/\.](0?[1-9]|[12][0-9]|3[01])[-/\.](19\d{2}|20\d{2})\b',
        
        # DD-MM-YYYY: European format
        r'\b(0?[1-9]|[12][0-9]|3[01])[-/\.](0?[1-9]|1[0-2])[-/\.](19\d{2}|20\d{2})\b',
        
        # Month name formats
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?,?\s+(19\d{2}|20\d{2})\b',
        r'\b(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?\s+(?:of\s+)?(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?,?\s+(19\d{2}|20\d{2})\b',
    ]
    
    print("\nTesting birthdate extraction:")
    for test in test_birthdates:
        # Normalize the transcript
        normalized = test.lower().replace('/', '-').replace('.', '-')
        
        extracted = None
        for pattern in date_patterns:
            match = re.search(pattern, normalized, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                if len(groups) == 3:
                    # Determine format type based on pattern
                    if pattern.startswith(r'\b(19\d{2}|20\d{2})'):  # YYYY-MM-DD
                        year, month, day = groups
                    elif pattern.startswith(r'\b(0?[1-9]|1[0-2])'):  # MM-DD-YYYY
                        month, day, year = groups
                    elif pattern.startswith(r'\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)'):  # Month DD, YYYY
                        month, day, year = groups
                    elif pattern.startswith(r'\b(0?[1-9]|[12][0-9]|3[01])(?:st|nd|rd|th)?\s+(?:of\s+)?'):  # DD Month YYYY
                        day, month, year = groups
                    else:  # DD-MM-YYYY
                        day, month, year = groups
                    
                    # Convert to proper format
                    if isinstance(month, str) and month.lower() in month_to_num:  # Month is a name
                        month = month_to_num[month.lower()]
                    
                    # Ensure two digits for month and day
                    month = str(month).zfill(2)
                    day = str(day).zfill(2)
                    
                    extracted = f"{year}-{month}-{day}"
                    break
        
        print(f"Input: '{test}' -> Extracted: '{extracted}'")

if __name__ == "__main__":
    test_name_extraction()
    test_phone_extraction()
    test_birthdate_extraction() 