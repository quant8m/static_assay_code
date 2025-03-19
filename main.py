import os
import argparse
import json
import re

try:
    import toml
except ImportError:
    toml = None

def detect_language(directory):
    language_extensions = {
        'Python': ['.py'],
        'JavaScript': ['.js', '.jsx'],
        'Java': ['.java'],
        'Ruby': ['.rb'],
        'Go': ['.go'],
        'C': ['.c', '.h'],
        'C++': ['.cpp', '.hpp', '.cc'],
        'TypeScript': ['.ts', '.tsx'],
        'PHP': ['.php'],
        'Rust': ['.rs'],
    }
    
    counts = {lang: 0 for lang in language_extensions}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            _, ext = os.path.splitext(file)
            for lang, exts in language_extensions.items():
                if ext.lower() in exts:
                    counts[lang] += 1
    
    if not sum(counts.values()):
        return None
    
    return max(counts, key=counts.get)

def find_dependency_files(directory, language):
    dependency_files_map = {
        'Python': ['requirements.txt', 'Pipfile', 'pyproject.toml'],
        'JavaScript': ['package.json', 'yarn.lock'],
        'Java': ['pom.xml', 'build.gradle'],
        'Ruby': ['Gemfile'],
        'Go': ['go.mod'],
        'TypeScript': ['package.json'],
    }
    
    targets = dependency_files_map.get(language, [])
    found_files = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file in targets:
                found_files.append(os.path.join(root, file))
    
    return found_files

def parse_python_file(file_path):
    dependencies = []
    file_name = os.path.basename(file_path)
    
    try:
        with open(file_path, 'r') as f:
            if file_name == 'requirements.txt':
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        parts = re.split(r'==|>=|<=|>|<|~=|!=', line, 1)
                        name = parts[0].strip()
                        version = parts[1].strip() if len(parts) > 1 else None
                        dependencies.append({
                            'name': name,
                            'version': version,
                            'source': file_name
                        })
            
            elif file_name == 'pyproject.toml' and toml:
                data = toml.load(f)
                if 'tool' in data and 'poetry' in data['tool']:
                    deps = data['tool']['poetry'].get('dependencies', {})
                    for name, spec in deps.items():
                        if name != 'python':
                            version = str(spec) if not isinstance(spec, dict) else None
                            dependencies.append({
                                'name': name,
                                'version': version,
                                'source': file_name
                            })
            
            elif file_name == 'Pipfile' and toml:
                data = toml.load(f)
                for section in ['packages', 'dev-packages']:
                    deps = data.get(section, {})
                    for name, spec in deps.items():
                        version = str(spec) if spec != '*' else None
                        dependencies.append({
                            'name': name,
                            'version': version,
                            'source': file_name
                        })
    
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
    
    return dependencies

def parse_javascript_file(file_path):
    dependencies = []
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            for section in ['dependencies', 'devDependencies']:
                deps = data.get(section, {})
                for name, version in deps.items():
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'source': os.path.basename(file_path)
                    })
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
    return dependencies

def parse_dependency_file(file_path, language):
    if language == 'Python':
        return parse_python_file(file_path)
    elif language in ['JavaScript', 'TypeScript']:
        return parse_javascript_file(file_path)
    return []

def extract_code_dependencies(directory, language):
    dependencies = []
    
    if language == 'Python':
        pattern = re.compile(r'^\s*(?:from|import)\s+([\w\.]+)')
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        for line in f:
                            match = pattern.match(line)
                            if match:
                                module = match.group(1).split('.')[0]
                                dependencies.append(module)
    
    elif language in ['JavaScript', 'TypeScript']:
        pattern = re.compile(r'''require\(['"](.+?)['"]\)|from\s+['"](.+?)['"]|import\s+['"](.+?)['"]''')
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(('.js', '.jsx', '.ts', '.tsx')):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        for match in matches:
                            for group in match:
                                if group:
                                    dependencies.append(group.split('/')[0])
    
    return [{'name': name, 'version': None, 'source': 'code'} 
            for name in set(dependencies)]

def main():
    parser = argparse.ArgumentParser(description='Project Dependency Analyzer')
    parser.add_argument('directory', help='Path to project directory')
    args = parser.parse_args()
    
    if not os.path.isdir(args.directory):
        print("Invalid directory path")
        return
    
    language = detect_language(args.directory)
    if not language:
        print("Could not detect project language")
        return
    
    dep_files = find_dependency_files(args.directory, language)
    dependencies = []
    for file_path in dep_files:
        dependencies.extend(parse_dependency_file(file_path, language))
    
    code_deps = extract_code_dependencies(args.directory, language)
    dependencies.extend(code_deps)
    
    seen = set()
    unique_deps = []
    for dep in dependencies:
        key = (dep['name'], dep['source'])
        if key not in seen:
            seen.add(key)
            unique_deps.append(dep)
    
    report = {
        'language': language,
        'dependencies': unique_deps
    }
    
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()

#Example of command: python3 main.py /home/xpenetrator/Documents/develop/my_prog > results.json
