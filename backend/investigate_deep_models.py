import os
import sys
import inspect
import hashlib
from pathlib import Path
import torch

sys.stdout.reconfigure(encoding="utf-8")

backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()

print("=" * 70)
print("1. IDENTIDADE REAL DAS CLASSES")
print("=" * 70)

from archs.hdrunet.UNet_arch import HDRUNet
from archs.safhdr.SAFHDR import HDRUNet as SAFHDR

print("HDRUNet module:", HDRUNet.__module__)
print("HDRUNet file:", inspect.getfile(HDRUNet))
print("HDRUNet class:", HDRUNet.__name__)
print()
print("SAFHDR module:", SAFHDR.__module__)
print("SAFHDR file:", inspect.getfile(SAFHDR))
print("SAFHDR class:", SAFHDR.__name__)

print("\n" + "=" * 70)
print("2. VERIFIQUE sys.path E ARQUIVOS FÍSICOS")
print("=" * 70)
print("sys.path atual:")
for i, p in enumerate(sys.path):
    print(f"  [{i}] {p}")

print("\nBusca física por UNet_arch.py e SAFHDR.py no sistema:")
search_roots = [
    os.path.abspath("backend"),
    os.path.abspath("."),
]
found_hdrunet = []
found_safhdr = []
for root in search_roots:
    if os.path.exists(root):
        for path in Path(root).rglob("UNet_arch.py"):
            found_hdrunet.append(str(path.resolve()))
        for path in Path(root).rglob("SAFHDR.py"):
            found_safhdr.append(str(path.resolve()))

print("Ocorrências de UNet_arch.py:")
for p in set(found_hdrunet):
    size = os.path.getsize(p)
    with open(p, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:16]
    print(f"  - {p} (tamanho: {size} bytes, sha256_prefix: {h})")

print("Ocorrências de SAFHDR.py:")
for p in set(found_safhdr):
    size = os.path.getsize(p)
    with open(p, "rb") as f:
        h = hashlib.sha256(f.read()).hexdigest()[:16]
    print(f"  - {p} (tamanho: {size} bytes, sha256_prefix: {h})")

print("\n" + "=" * 70)
print("3. VERIFIQUE __file__")
print("=" * 70)
import services.hdr_service
hdrunet_mod = sys.modules.get('archs.hdrunet.UNet_arch')
safhdr_mod = sys.modules.get('archs.safhdr.SAFHDR')

print("services.hdr_service.__file__   :", services.hdr_service.__file__)
print("archs.hdrunet.UNet_arch file    :", getattr(hdrunet_mod, '__file__', inspect.getfile(HDRUNet)))
print("archs.safhdr.SAFHDR file        :", getattr(safhdr_mod, '__file__', inspect.getfile(SAFHDR)))

print("\n" + "=" * 70)
print("4. COMPARE AS CLASSES (ESTRUTURAL)")
print("=" * 70)
hdr_inst = HDRUNet()
saf_inst = SAFHDR()

hdr_submodules = {n: m.__class__.__name__ for n, m in hdr_inst.named_children()}
saf_submodules = {n: m.__class__.__name__ for n, m in saf_inst.named_children()}

print("Submódulos diretos de HDRUNet:")
for n, c in hdr_submodules.items():
    print(f"  - {n}: {c}")

print("\nSubmódulos diretos de SAFHDR:")
for n, c in saf_submodules.items():
    print(f"  - {n}: {c}")

hdr_exclusive_sub = set(hdr_submodules.keys()) - set(saf_submodules.keys())
saf_exclusive_sub = set(saf_submodules.keys()) - set(hdr_submodules.keys())
common_sub = set(hdr_submodules.keys()) & set(saf_submodules.keys())

print(f"\nSubmódulos exclusivos HDRUNet ({len(hdr_exclusive_sub)}): {sorted(list(hdr_exclusive_sub))}")
print(f"Submódulos exclusivos SAFHDR ({len(saf_exclusive_sub)}): {sorted(list(saf_exclusive_sub))}")
print(f"Submódulos em comum ({len(common_sub)}): {sorted(list(common_sub))}")

print("\n" + "=" * 70)
print("5. COMPARE O forward()")
print("=" * 70)
print("--- HDRUNet.forward ---")
print(inspect.getsource(HDRUNet.forward))
print("--- SAFHDR.forward ---")
print(inspect.getsource(SAFHDR.forward))

print("\n" + "=" * 70)
print("6. COMPARE O NÚMERO DE PARÂMETROS")
print("=" * 70)
hdr_params = sum(p.numel() for p in hdr_inst.parameters())
saf_params = sum(p.numel() for p in saf_inst.parameters())

print("HDRUNet total params:", hdr_params)
print("SAFHDR total params :", saf_params)
print("Diferença absoluta  :", abs(hdr_params - saf_params))
