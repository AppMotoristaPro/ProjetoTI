import os

# Arquivo de saida
OUTPUT_FILE = "codigo_completo.txt"

# Pastas e extensoes para ignorar (evita ler binarios e dependencias)
IGNORE_DIRS = {'.git', '__pycache__', 'node_modules', 'venv', 'env', '.idea', 'build', 'dist', '.gradle'}
IGNORE_EXTS = {
    '.pyc', '.png', '.jpg', '.jpeg', '.gif', '.apk', '.exe', '.dll', '.so', 
    '.zip', '.tar', '.gz', '.db', '.sqlite3', '.mp3', '.mp4', '.ttf'
}

def generate_tree(startpath, prefix=''):
    """Gera a estrutura de pastas no formato tree."""
    tree_str = ""
    try:
        items = sorted(os.listdir(startpath))
    except PermissionError:
        return ""

    # Filtra pastas ocultas e pastas ignoradas
    items = [f for f in items if f not in IGNORE_DIRS and not f.startswith('.')]

    for i, item in enumerate(items):
        path = os.path.join(startpath, item)
        is_last = (i == len(items) - 1)
        connector = "└── " if is_last else "├── "
        tree_str += prefix + connector + item + "\n"

        if os.path.isdir(path):
            extension = "    " if is_last else "│   "
            tree_str += generate_tree(path, prefix + extension)
            
    return tree_str

def extract_code(startpath):
    """Lê o conteúdo dos arquivos permitidos."""
    code_str = ""
    for root, dirs, files in os.walk(startpath):
        # Modifica a lista de diretorios in-place para o os.walk ignorar as pastas pesadas
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith('.')]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            
            # Pula o proprio arquivo gerado e extensoes bloqueadas
            if ext in IGNORE_EXTS or file == OUTPUT_FILE or file == os.path.basename(__file__):
                continue

            filepath = os.path.join(root, file)
            
            try:
                # Tenta ler como texto (UTF-8)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                rel_path = os.path.relpath(filepath, startpath)
                code_str += f"\n{'='*60}\n"
                code_str += f"ARQUIVO: {rel_path}\n"
                code_str += f"{'='*60}\n\n"
                code_str += content + "\n"
                
            except UnicodeDecodeError:
                # Se falhar ao ler como UTF-8, é um binário que passou no filtro, apenas ignoramos
                pass
            except Exception as e:
                code_str += f"\n[Erro ao ler {filepath}: {e}]\n"
                
    return code_str

def main():
    current_dir = os.getcwd()
    print(f"Analisando arquivos na pasta: {current_dir}...")
    
    # 1. Gera a arvore do projeto
    tree_output = "ESTRUTURA DO PROJETO:\n"
    tree_output += f"{os.path.basename(current_dir)}/\n" + generate_tree(current_dir)
    
    # 2. Extrai os codigos
    print("Extraindo códigos-fonte...")
    code_output = extract_code(current_dir)
    
    # 3. Junta tudo e salva
    final_output = tree_output + "\n\nCÓDIGOS-FONTE:\n" + code_output
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_output)
        
    print(f"\nSucesso! Tudo foi salvo no arquivo: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

