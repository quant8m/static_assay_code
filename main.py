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
        'Rust': ['Cargo.toml'],
        'TypeScript': ['package.json']
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


def parse_ruby_file(file_path):
    dependencies = []
    file_name = os.path.basename(file_path)
    
    try:
        with open(file_path, 'r') as f:
            if file_name == 'Gemfile':
                for line in f:
                    line = line.strip()
                    if line.startswith('gem '):
                        match = re.match(r"gem\s+['\"]([^'\"]+)['\"]", line)
                        if match:
                            name = match.group(1)
                            version_match = re.search(r",\s*['\"]([^'\"]+)['\"]", line)
                            version = version_match.group(1) if version_match else None
                            dependencies.append({
                                'name': name,
                                'version': version,
                                'source': file_name
                            })
            
            elif file_name == 'Gemfile.lock':
                in_gems = False
                for line in f:
                    line = line.strip()
                    if line == 'GEMS':
                        in_gems = True
                    elif in_gems and line.startswith('specs:'):
                        continue
                    elif in_gems and line == '':
                        break
                    elif in_gems:
                        parts = line.split()
                        if len(parts) >= 2:
                            name = parts[0]
                            version = parts[1].strip('()')
                            dependencies.append({
                                'name': name,
                                'version': version,
                                'source': file_name
                            })
    
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
    
    return dependencies


def parse_java_file(file_path):
    dependencies = []
    file_name = os.path.basename(file_path)
    
    try:
        if file_name == 'pom.xml':
            tree = ET.parse(file_path)
            root = tree.getroot()
            ns = {'mvn': 'http://maven.apache.org/POM/4.0.0'}
            
            for dep in root.findall('.//mvn:dependency', ns):
                group_id = dep.find('mvn:groupId', ns).text
                artifact_id = dep.find('mvn:artifactId', ns).text
                version_elem = dep.find('mvn:version', ns)
                version = version_elem.text if version_elem is not None else None
                
                dependencies.append({
                    'name': f"{group_id}:{artifact_id}",
                    'version': version,
                    'source': file_name
                })
        
        elif file_name in ('build.gradle', 'build.gradle.kts'):
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    match = re.match(
                        r"(implementation|compile|api)\s+['\"]([^:]+):([^:]+)(?::([^'\"]+))?['\"]", 
                        line
                    )
                    if match:
                        group = match.group(2)
                        artifact = match.group(3)
                        version = match.group(4) or None
                        dependencies.append({
                            'name': f"{group}:{artifact}",
                            'version': version,
                            'source': file_name
                        })
    
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
    
    return dependencies


def parse_go_mod(file_path):
    dependencies = []
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('require ('):
                    for line in f:
                        line = line.strip()
                        if line == ')':
                            break
                        if line and not line.startswith('//'):
                            parts = line.split()
                            if len(parts) >= 2:
                                name = parts[0]
                                version = parts[1]
                                dependencies.append({
                                    'name': name,
                                    'version': version,
                                    'source': 'go.mod'
                                })
                elif line.startswith('require'):
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[1]
                        version = parts[2]
                        dependencies.append({
                            'name': name,
                            'version': version,
                            'source': 'go.mod'
                        })
    except Exception as e:
        print(f"Error parsing {file_path}: {str(e)}")
    return dependencies

def parse_rust_cargo_toml(file_path):
    dependencies = []
    try:
        with open(file_path, 'r') as f:
            data = toml.load(f)
            for section in ['dependencies', 'dev-dependencies', 'build-dependencies']:
                deps = data.get(section, {})
                for name, spec in deps.items():
                    version = None
                    if isinstance(spec, str):
                        version = spec
                    elif isinstance(spec, dict):
                        version = spec.get('version')
                    dependencies.append({
                        'name': name,
                        'version': version,
                        'source': 'Cargo.toml'
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
    elif language == 'Go':
        return parse_go_mod(file_path)
    elif language == 'Rust':
        return parse_rust_cargo_toml(file_path)   
    elif language == 'Ruby':
        return parse_ruby_file(file_path)
    elif language == 'Java':
        return parse_java_file(file_path)
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
    elif language == 'Go':
        pattern = re.compile(r'^\s*import\s+["(](.+?)[")]')
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.go'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        for line in f:
                            match = pattern.search(line)
                            if match:
                                imports = match.group(1).split('\n')
                                for imp in imports:
                                    imp = imp.strip()
                                    if imp:
                                        parts = imp.split()
                                        if len(parts) > 0:
                                            dep = parts[0].replace('"', '')
                                            dependencies.append(dep.split('/')[0])
    
    
    elif language == 'Rust':
        patterns = [
            re.compile(r'^\s*use\s+([\w:]+)'),
            re.compile(r'^\s*extern\s+crate\s+([\w_]+)')
        ]
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.rs'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        content = f.read()
                        for pattern in patterns:
                            matches = pattern.findall(content)
                            for match in matches:
                                dep = match.split('::')[0]
                                dependencies.append(dep)
    
    elif language == 'Ruby':
        pattern = re.compile(r'^\s*(?:require|require_relative)\s+[\'"](.+?)[\'"]')
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.rb'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        for line in f:
                            match = pattern.match(line)
                            if match:
                                dep = match.group(1).split('/')[0]
                                dependencies.append(dep)

    elif language == 'Java':
        package_pattern = re.compile(r'^\s*package\s+([\w.]+)\s*;')
        import_pattern = re.compile(r'^\s*import\s+(?:static\s+)?([\w.*]+)\s*;')
        
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith('.java'):
                    with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                        current_package = None
                        for line in f:
                            package_match = package_pattern.match(line)
                            if package_match:
                                current_package = package_match.group(1)
                            
                            import_match = import_pattern.match(line)
                            if import_match:
                                full_class = import_match.group(1)
                                if '.' in full_class:
                                    dep = full_class.rsplit('.', 1)[0]
                                    dependencies.append(dep)
    
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
