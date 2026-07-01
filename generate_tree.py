import os

# المجلدات والملفات التي نريد تجاهلها
IGNORE_DIRS = {'venv', '.venv', 'node_modules', '.git', '__pycache__', '.next', 'dist', 'build'}
IGNORE_FILES = {'.DS_Store', 'generate_tree.py'}

def generate_tree(startpath, prefix=''):
    tree_str = ""
    try:
        items = sorted(os.listdir(startpath))
    except PermissionError:
        return ""

    # فلترة المجلدات والملفات
    items = [id for id in items if id not in IGNORE_DIRS and id not in IGNORE_FILES]
    
    for i, item in enumerate(items):
        path = os.path.join(startpath, item)
        is_last = i == (len(items) - 1)
        connector = '└── ' if is_last else '├── '
        
        tree_str += f"{prefix}{connector}{item}\n"
        
        if os.path.isdir(path):
            extension = '    ' if is_last else '│   '
            tree_str += generate_tree(path, prefix=prefix + extension)
            
    return tree_str

if __name__ == '__main__':
    project_root = '.'  # مسار المشروع الحالي
    tree_output = f"{os.path.basename(os.path.abspath(project_root))}/\n"
    tree_output += generate_tree(project_root)
    
    # حفظ النتيجة في ملف نصي
    with open('project_tree.txt', 'w', encoding='utf-8') as f:
        f.write(tree_output)
        
    print("✅ تم استخراج شجرة المشروع بنجاح في ملف: project_tree.txt")