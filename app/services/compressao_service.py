import io
from PIL import Image
from pypdf import PdfReader, PdfWriter

def comprimir_arquivo(arquivo_storage):
    """
    Recebe o arquivo vindo do formulário HTML.
    Comprime (Imagem ou PDF) e retorna os bytes otimizados e o mimetype final.
    """
    mimetype = arquivo_storage.mimetype
    nome_arquivo = arquivo_storage.filename.lower()
    
    # Lê os bytes originais que o usuário enviou
    bytes_iniciais = arquivo_storage.read()
    
    # 1. COMPRESSÃO DE IMAGENS (PNG, JPG, JPEG)
    if mimetype.startswith('image/'):
        try:
            # Abre a imagem usando a biblioteca Pillow
            img = Image.open(io.BytesIO(bytes_iniciais))
            
            # Se a imagem for PNG com fundo transparente, converte para RGB para salvar como JPG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Redimensiona limitando a 1200 pixels (mantém qualidade para ler textos, mas derruba o peso)
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            # Salva como JPEG com 70% de qualidade e otimização ativada
            img.save(output, format="JPEG", quality=70, optimize=True)
            
            return output.getvalue(), 'image/jpeg'
        
        except Exception as e:
            print(f"⚠️ Erro ao comprimir imagem: {e}")
            return bytes_iniciais, mimetype # Se falhar, salva o original para não perder o comprovante

    # 2. COMPRESSÃO DE PDF
    elif mimetype == 'application/pdf' or nome_arquivo.endswith('.pdf'):
        try:
            leitor = PdfReader(io.BytesIO(bytes_iniciais))
            escritor = PdfWriter()
            
            for pagina in leitor.pages:
                # Remove espaços em branco e comprime as linhas de código do PDF
                pagina.compress_content_streams()
                escritor.add_page(pagina)
                
            output = io.BytesIO()
            escritor.write(output)
            
            return output.getvalue(), 'application/pdf'
            
        except Exception as e:
            print(f"⚠️ Erro ao comprimir PDF: {e}")
            return bytes_iniciais, mimetype

    # 3. OUTROS FORMATOS
    # Se você enviar algo diferente (ex: um txt), ele apenas devolve como chegou
    return bytes_iniciais, mimetype

