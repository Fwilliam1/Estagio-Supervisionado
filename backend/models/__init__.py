# backend/models/__init__.py

def __getattr__(name):
    if name == 'Usuario':
        from .usuario import Usuario
        return Usuario
    elif name == 'Algoritmo':
        from .algoritmo import Algoritmo
        return Algoritmo
    elif name == 'Imagem':
        from .imagem import Imagem
        return Imagem
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
