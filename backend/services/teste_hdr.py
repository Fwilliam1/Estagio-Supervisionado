import sys
import os
import time

# 1. Configura os caminhos para o Python encontrar os pacotes do projeto
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, '..'))
root_dir = os.path.abspath(os.path.join(current_dir, '..', '..'))

for p in [backend_dir, root_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

# 2. Inicialização do Django com registro da pasta 'models'
try:
    import django
    from django.conf import settings

    django_pronto = False
    possible_modules = ["backend.settings", "settings", "config.settings", "core.settings"]

    for mod in possible_modules:
        try:
            os.environ["DJANGO_SETTINGS_MODULE"] = mod
            django.setup()
            django_pronto = True
            break
        except Exception:
            continue

    if not django_pronto and not settings.configured:
        settings.configure(
            INSTALLED_APPS=[
                'django.contrib.contenttypes',
                'django.contrib.auth',
                'models',
            ],
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3',
                    'NAME': ':memory:',
                }
            }
        )
        django.setup()

except Exception as e:
    print(f"Aviso de configuração do Django: {e}")

# 3. Importação do Serviço HDR
try:
    from services.hdr_service import HDRService
except Exception as e:
    print(f"Erro detalhado ao importar o serviço: {e}")
    exit(1)


def main():
    # Caminho da imagem de entrada (certifique-se de usar a extensão correta .jpg ou .png)
    caminho_entrada = "0212_medium.png" 
    caminho_saida = "resultado_teste_safhdr_0212.png"

    # Verifica se a imagem realmente está no local correto
    if not os.path.exists(caminho_entrada):
        print(f"❌ Erro: O arquivo '{caminho_entrada}' não foi encontrado.")
        print(f"Por favor, salve a imagem na pasta onde você está rodando o terminal: {os.getcwd()}")
        return

    print(f"[*] Lendo a imagem: {caminho_entrada}")
    with open(caminho_entrada, "rb") as f:
        image_bytes = f.read()

    print("[*] Processando via SAFHDR...")
    
    try:
        # Alterado para acionar o SAFHDR
        resultado = HDRService.processar_imagem(
            image_bytes=image_bytes,
            model_name='SAFHDR',
            tone_mapping='reinhard'
        )
        
        print("\n✅ Processamento concluído!")
        print("-" * 40)
        print(f"🔹 Modelo Base utilizado: {resultado.get('modelo_hdr')}")
        print(f"🔹 Tone Mapping: {resultado.get('tone_mapping')}")
        print(f"🔹 Dispositivo: {resultado.get('dispositivo')}")
        print(f"🔹 Resolução: {resultado.get('resolucao_processada')}")
        print(f"🔹 Tempo de inferência: {resultado.get('tempo_processamento')}s")
        print("-" * 40)

        # Validação ajustada para SAFHDR
        if resultado.get('modelo_hdr') == 'SAFHDR':
            print("✔️ SUCESSO: A rede SAFHDR processou a imagem real com sucesso!")
        else:
            print(f"❌ FALHA: O serviço executou outro modelo: {resultado.get('modelo_hdr')}")

        with open(caminho_saida, "wb") as f_out:
            f_out.write(resultado["imagem_processada_bytes"])
        
        print(f"\n📁 Saída gerada em: {os.path.abspath(caminho_saida)}")

    except Exception as e:
        print(f"\n❌ Erro durante a execução: {str(e)}")

if __name__ == "__main__":
    main()