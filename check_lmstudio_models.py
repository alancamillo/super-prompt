#!/usr/bin/env python3
"""
Script para verificar modelos disponíveis no LM Studio
Use este script para descobrir o nome exato do modelo que você precisa usar
"""

import requests
import json
import sys

def check_models(api_base: str = "http://localhost:1234/v1"):
    """
    Verifica quais modelos estão disponíveis no servidor LM Studio.
    
    Args:
        api_base: URL base da API do LM Studio
    """
    try:
        response = requests.get(f"{api_base}/models", timeout=5)
        response.raise_for_status()
        data = response.json()
        
        print(f"\n{'='*80}")
        print(f"Modelos disponíveis em {api_base}")
        print(f"{'='*80}\n")
        
        if "data" in data:
            for model in data["data"]:
                model_id = model.get("id", "N/A")
                print(f"  ✓ {model_id}")
            
            print(f"\n{'='*80}")
            print(f"Total: {len(data['data'])} modelo(s)")
            print(f"{'='*80}\n")
            
            # Salva em arquivo JSON para referência
            with open("lmstudio_models.json", "w") as f:
                json.dump(data, f, indent=2)
            print("📝 Lista salva em: lmstudio_models.json\n")
            
            return data["data"]
        else:
            print("❌ Formato de resposta inesperado")
            print(json.dumps(data, indent=2))
            return []
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Erro: Não foi possível conectar a {api_base}")
        print("   Certifique-se de que o LM Studio está rodando e o servidor está ativo.")
        return []
    except requests.exceptions.Timeout:
        print(f"❌ Erro: Timeout ao conectar a {api_base}")
        return []
    except Exception as e:
        print(f"❌ Erro: {e}")
        return []

if __name__ == "__main__":
    # Pode passar a URL como argumento
    api_base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:1234/v1"
    
    # Para servidor remoto, use: http://spark-0852.local:1234/v1
    if len(sys.argv) > 1:
        api_base = sys.argv[1]
    elif "spark" in api_base or "local" in api_base:
        # Se você quiser verificar um servidor remoto por padrão, ajuste aqui
        pass
    
    check_models(api_base)

