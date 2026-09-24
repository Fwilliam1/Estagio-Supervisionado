import os
import time
from PIL import Image

# Importa o seu serviço. Adapte a linha abaixo se a estrutura de pastas for diferente.
try:
    from hdr_service import HDRService
except ImportError:
    print("Erro: Não foi possível importar o HDRService. Coloque este script na mesma pasta que hdr_service.py.")
    exit(1)

def criar_imagem_teste(caminho: str):
    """Cria uma imagem de teste simples com gradiente caso o usuário não tenha uma."""
    img = Image.new('RGB', (800, 600), color=(73, 109, 137))
    img.save(caminho)
    print(f"[*] Imagem de teste criada automaticamente em: {caminho}")

def main():
    caminho_entrada = "imagem_teste_entrada.jpg"
    caminho_saida = "resultado_teste_pshdr.png"

    # 1. Garante que temos uma imagem para testar
    if not os.path.exists(caminho_entrada):
        criar_imagem_teste(caminho_entrada)

    print(f"[*] Lendo a imagem: {caminho_entrada}")
    with open(caminho_entrada, "rb") as f:
        image_bytes = f.read()

    print("[*] Iniciando o processamento HDR (Isso pode levar alguns segundos na primeira execução para carregar os pesos)...")
    start_time = time.time()
    
    try:
        # 2. Chama o serviço exigindo explicitamente o PSHDR
        resultado = HDRService.processar_imagem(
            image_bytes=image_bytes,
            model_name='PSHDR',       # Força o PSHDR
            tone_mapping='reinhard'
        )
        
        end_time = time.time()

        print("\n✅ Processamento concluído!")
        print("-" * 40)
        print(f"🔹 Modelo Base utilizado: {resultado.get('modelo_hdr')}")
        print(f"🔹 Tone Mapping: {resultado.get('tone_mapping')}")
        print(f"🔹 Dispositivo: {resultado.get('dispositivo')}")
        print(f"🔹 Resolução: {resultado.get('resolucao_processada')}")
        print(f"🔹 Tempo da inferência: {resultado.get('tempo_processamento')}s")
        print("-" * 40)

        # 3. Validação Automática
        if resultado.get('modelo_hdr') == 'PSHDR':
            print("✔️ SUCESSO: A rede PSHDR foi instanciada de forma isolada corretamente!")
        else:
            print(f"❌ FALHA: O serviço ainda está usando a rede: {resultado.get('modelo_hdr')}")

        # 4. Salva a saída no disco
        with open(caminho_saida, "wb") as f_out:
            f_out.write(resultado["imagem_processada_bytes"])
        
        print(f"\n📁 A imagem processada foi salva em: {caminho_saida}")

    except Exception as e:
        print(f"\n❌ Erro durante o processamento: {str(e)}")

if __name__ == "__main__":
    main()