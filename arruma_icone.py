from PIL import Image
import os

# Caminho do seu icone
caminho_icone = "app/static/icons/icone.png"

def otimizar_icone():
    if not os.path.exists(caminho_icone):
        print(f"❌ Ícone não encontrado em: {caminho_icone}")
        return

    try:
        # Abre a imagem
        img = Image.open(caminho_icone).convert("RGBA")
        
        # Identifica a área real da imagem (ignora toda a transparência extra ao redor)
        caixa_delimitadora = img.getbbox()
        
        if caixa_delimitadora:
            # Corta a imagem tirando o excesso de borda transparente
            img = img.crop(caixa_delimitadora)
            
        # Redimensiona forçando o tamanho padrão PWA (512x512) mantendo a qualidade
        img = img.resize((512, 512), Image.Resampling.LANCZOS)
        
        # Salva a nova imagem por cima da antiga
        img.save(caminho_icone, "PNG")
        print("✅ Ícone ajustado, cortado e redimensionado para 512x512 com sucesso!")
        
    except Exception as e:
        print(f"❌ Ocorreu um erro: {e}")

if __name__ == "__main__":
    otimizar_icone()

