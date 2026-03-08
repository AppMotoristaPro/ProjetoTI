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
    
    try:
        # Lê os bytes originais que o utilizador enviou
        bytes_iniciais = arquivo_storage.read()
    except Exception:
        return None, None
        
    if not bytes_iniciais:
        return None, None
    
    # 1. COMPRESSÃO DE IMAGENS (PNG, JPG, JPEG)
    if mimetype and mimetype.startswith('image/'):
        try:
            img = Image.open(io.BytesIO(bytes_iniciais))
            
            # Se a imagem for PNG com fundo transparente, converte para RGB para salvar como JPG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            # Redimensiona limitando a 1200 pixels (mantém qualidade, mas derruba o peso)
            max_size = (1200, 1200)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=70, optimize=True)
            
            return output.getvalue(), 'image/jpeg'
        
        except Exception as e:
            print(f"⚠️ Erro ao comprimir imagem. Acionando Plano B (Original): {e}")
            return bytes_iniciais, mimetype 

    # 2. COMPRESSÃO DE PDF (Blindada)
    elif mimetype == 'application/pdf' or nome_arquivo.endswith('.pdf'):
        try:
            leitor = PdfReader(io.BytesIO(bytes_iniciais))
            escritor = PdfWriter()
            
            for pagina in leitor.pages:
                try:
                    # Tenta comprimir. Se a página for protegida ou ilegível, ignora o erro e avança.
                    pagina.compress_content_streams()
                except Exception:
                    pass
                escritor.add_page(pagina)
                
            output = io.BytesIO()
            escritor.write(output)
            
            return output.getvalue(), 'application/pdf'
            
        except Exception as e:
            print(f"⚠️ Erro estrutural no PDF. Acionando Plano B (Original): {e}")
            return bytes_iniciais, mimetype

    # 3. OUTROS FORMATOS
    return bytes_iniciais, mimetype


