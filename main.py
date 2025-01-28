import re
import os
from typing import List, Optional


LANGUAGE_PATTERNS = {
    'python': re.compile(r'^\s*(?:from\s+([\w\.]+)\s+)?import\s+([\w\.]+)'),
    'javascript': re.compile(r'^\s*(?:import\s+[\w\s{},*]+\s+from\s+)?[\'"]([^"\']+)[\'"]'),
    'java': re.compile(r'^\s*import\s+([\w\.]+);'),
    'c++': re.compile(r'^\s*#include\s+[<"]([^">]+)[">]'),
    'ruby': re.compile(r'^\s*require\s+[\'"]([^"\']+)[\'"]'),
    'go': re.compile(r'^\s*import\s+[\'"]([^"\']+)[\'"]'),
    'c': re.compile(r'^\s*#include\s+[<"]([^">]+)[">]'),
    'c#': re.compile(r'^\s*using\s+([\w\.]+);'),
    'php': re.compile(r'^\s*(?:require|require_once|include|include_once)\s*[\'"]([^"\']+)[\'"]')
}

def detect_language(filename: str) -> Optional[str]:
    extensions = {
        '.py': 'python',
        '.js': 'javascript',
        '.java': 'java',
        '.cpp': 'c++',
        '.rb': 'ruby',
        '.go': 'go',
        '.c' : 'c',
        '.cs': 'c#',
        '.php': 'php'
    }
    for ext, lang in extensions.items():
        if filename.endswith(ext):
            return lang
    return None

def extract_libraries(code: str, language: str) -> List[str]:
    pattern = LANGUAGE_PATTERNS.get(language)
    if not pattern:
        return []
    
    libraries = set()
    for line in code.splitlines():
        match = pattern.match(line)
        if match:
            library = match.group(1) if match.group(1) else match.group(2)
            libraries.add(library)
    return sorted(libraries)

def analyze_file(file_path: str):
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return
    
    language = detect_language(file_path)
    if not language:
        print(f"Unsupported file type: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as file:
        code = file.read()
    
    libraries = extract_libraries(code, language)
    if libraries:
        print(f"Detected libraries in {file_path} ({language}):")
        for lib in libraries:
            print(f" - {lib}")
    else:
        print(f"No libraries detected in {file_path}.")

if __name__ == "__main__":
    file_path = input("Enter the path to the file: ").strip()
    analyze_file(file_path)
