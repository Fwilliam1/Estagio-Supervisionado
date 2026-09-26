import os
import sys
import inspect
import hashlib
from pathlib import Path
import torch
import torch.nn as nn

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

from archs.pshdr.PSHDR import HDRUNet as PSHDR
from archs.safhdr.SAFHDR import HDRUNet as SAFHDR

print("PSHDR module:", PSHDR.__module__)
print("PSHDR file:", inspect.getfile(PSHDR))
print("PSHDR class:", PSHDR.__name__)
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

print("\nBusca física por PSHDR.py e SAFHDR.py no sistema:")
search_roots = [
    os.path.abspath("backend"),
    r"C:\Users\Emanuel Ramos\Desktop\PSHDR",
    os.path.abspath("."),
]
found_pshdr = []
found_safhdr = []
for root in search_roots:
    if os.path.exists(root):
        for path in Path(root).rglob("PSHDR.py"):
            found_pshdr.append(str(path.resolve()))
        for path in Path(root).rglob("SAFHDR.py"):
            found_safhdr.append(str(path.resolve()))

print("Ocorrências de PSHDR.py:")
for p in set(found_pshdr):
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
pshdr_mod = sys.modules.get('archs.pshdr.PSHDR')
safhdr_mod = sys.modules.get('archs.safhdr.SAFHDR')

print("services.hdr_service.__file__ :", services.hdr_service.__file__)
print("archs.pshdr.PSHDR file        :", getattr(pshdr_mod, '__file__', inspect.getfile(PSHDR)))
print("archs.safhdr.SAFHDR file      :", getattr(safhdr_mod, '__file__', inspect.getfile(SAFHDR)))

print("\n" + "=" * 70)
print("4. COMPARE AS CLASSES (ESTRUTURAL)")
print("=" * 70)
ps_inst = PSHDR()
saf_inst = SAFHDR()

ps_submodules = {n: m.__class__.__name__ for n, m in ps_inst.named_children()}
saf_submodules = {n: m.__class__.__name__ for n, m in saf_inst.named_children()}

print("Submódulos diretos de PSHDR:")
for n, c in ps_submodules.items():
    print(f"  - {n}: {c}")

print("\nSubmódulos diretos de SAFHDR:")
for n, c in saf_submodules.items():
    print(f"  - {n}: {c}")

ps_exclusive_sub = set(ps_submodules.keys()) - set(saf_submodules.keys())
saf_exclusive_sub = set(saf_submodules.keys()) - set(ps_submodules.keys())
common_sub = set(ps_submodules.keys()) & set(saf_submodules.keys())

print(f"\nSubmódulos exclusivos PSHDR ({len(ps_exclusive_sub)}): {sorted(list(ps_exclusive_sub))}")
print(f"Submódulos exclusivos SAFHDR ({len(saf_exclusive_sub)}): {sorted(list(saf_exclusive_sub))}")
print(f"Submódulos em comum ({len(common_sub)}): {sorted(list(common_sub))}")

print("\n" + "=" * 70)
print("5. COMPARE O forward()")
print("=" * 70)
print("--- PSHDR.forward ---")
print(inspect.getsource(PSHDR.forward))
print("--- SAFHDR.forward ---")
print(inspect.getsource(SAFHDR.forward))

print("\n" + "=" * 70)
print("6. COMPARE A HERANÇA (__mro__)")
print("=" * 70)
print("PSHDR.__mro__ :", PSHDR.__mro__)
print("SAFHDR.__mro__:", SAFHDR.__mro__)

print("\n" + "=" * 70)
print("7. COMPARE O NÚMERO DE PARÂMETROS")
print("=" * 70)
ps_params = sum(p.numel() for p in ps_inst.parameters())
saf_params = sum(p.numel() for p in saf_inst.parameters())

print("PSHDR total params :", ps_params)
print("SAFHDR total params:", saf_params)
print("Diferença absoluta :", abs(ps_params - saf_params))

ps_named = list(ps_inst.named_parameters())
saf_named = list(saf_inst.named_parameters())
print("len(ps.named_parameters())  :", len(ps_named))
print("len(saf.named_parameters()) :", len(saf_named))

print("\n" + "=" * 70)
print("8. COMPARE OS NOMES E SHAPES DOS PARÂMETROS")
print("=" * 70)
ps_dict = {n: tuple(p.shape) for n, p in ps_named}
saf_dict = {n: tuple(p.shape) for n, p in saf_named}

ps_exclusive_params = set(ps_dict.keys()) - set(saf_dict.keys())
saf_exclusive_params = set(saf_dict.keys()) - set(ps_dict.keys())
common_param_names = set(ps_dict.keys()) & set(saf_dict.keys())

shape_mismatches = []
shape_matches = []
for k in sorted(list(common_param_names)):
    if ps_dict[k] != saf_dict[k]:
        shape_mismatches.append((k, ps_dict[k], saf_dict[k]))
    else:
        shape_matches.append(k)

print(f"Parâmetros exclusivos PSHDR ({len(ps_exclusive_params)}):")
for k in sorted(list(ps_exclusive_params))[:10]:
    print(f"  - {k}: {ps_dict[k]}")
if len(ps_exclusive_params) > 10:
    print(f"  ... e mais {len(ps_exclusive_params)-10} parâmetros.")

print(f"\nParâmetros exclusivos SAFHDR ({len(saf_exclusive_params)}):")
for k in sorted(list(saf_exclusive_params))[:10]:
    print(f"  - {k}: {saf_dict[k]}")
if len(saf_exclusive_params) > 10:
    print(f"  ... e mais {len(saf_exclusive_params)-10} parâmetros.")

print(f"\nParâmetros com mesmo nome mas SHAPES DIFERENTES ({len(shape_mismatches)}):")
for k, s_ps, s_saf in shape_mismatches[:10]:
    print(f"  - {k}: PSHDR={s_ps} vs SAFHDR={s_saf}")
if len(shape_mismatches) > 10:
    print(f"  ... e mais {len(shape_mismatches)-10} incompatibilidades.")

print(f"\nParâmetros idênticos em nome e shape: {len(shape_matches)}")

print("\n" + "=" * 70)
print("9 & 10. INVESTIGUE E COMPARE OS CHECKPOINTS")
print("=" * 70)
ckpt_ps_path = os.path.abspath("backend/pretrained_models/PSHDR_G.pth")
ckpt_saf_path = os.path.abspath("backend/pretrained_models/model_tm_406392_G.pth")

print("PSHDR Checkpoint   :", ckpt_ps_path)
print("  Tamanho          :", os.path.getsize(ckpt_ps_path), "bytes")
with open(ckpt_ps_path, "rb") as f:
    print("  SHA-256          :", hashlib.sha256(f.read()).hexdigest())

print("SAFHDR Checkpoint  :", ckpt_saf_path)
print("  Tamanho          :", os.path.getsize(ckpt_saf_path), "bytes")
with open(ckpt_saf_path, "rb") as f:
    print("  SHA-256          :", hashlib.sha256(f.read()).hexdigest())

sd_ps_raw = torch.load(ckpt_ps_path, map_location="cpu")
sd_saf_raw = torch.load(ckpt_saf_path, map_location="cpu")

print("\nChaves de nível superior no PSHDR checkpoint :", list(sd_ps_raw.keys()))
print("Chaves de nível superior no SAFHDR checkpoint:", list(sd_saf_raw.keys()))

sd_ps = sd_ps_raw["params"] if "params" in sd_ps_raw else sd_ps_raw
sd_saf = sd_saf_raw["params"] if "params" in sd_saf_raw else sd_saf_raw

print(f"Número de tensores em PSHDR state_dict : {len(sd_ps)}")
print(f"Número de tensores em SAFHDR state_dict: {len(sd_saf)}")

total_ps_ckpt_params = sum(t.numel() for t in sd_ps.values())
total_saf_ckpt_params = sum(t.numel() for t in sd_saf.values())
print(f"Total elementos numéricos em PSHDR : {total_ps_ckpt_params}")
print(f"Total elementos numéricos em SAFHDR: {total_saf_ckpt_params}")

# Comparação numérica de tensores que tenham mesmo nome e mesmo shape
num_equal = 0
num_diff = 0
mae_list = []
for k in shape_matches:
    if k in sd_ps and k in sd_saf:
        t_ps = sd_ps[k].float()
        t_saf = sd_saf[k].float()
        if torch.equal(t_ps, t_saf):
            num_equal += 1
        else:
            num_diff += 1
            mae = torch.mean(torch.abs(t_ps - t_saf)).item()
            mae_list.append(mae)

print(f"\nComparação numérica dos {len(shape_matches)} tensores com mesmo nome e shape:")
print(f"  - Exatamente iguais (torch.equal): {num_equal}")
print(f"  - Diferentes numericamente        : {num_diff}")
if mae_list:
    print(f"  - Diferença média absoluta (MAE) : {sum(mae_list)/len(mae_list):.6f}")
    print(f"  - MAE máximo entre camadas       : {max(mae_list):.6f}")

print("\n" + "=" * 70)
print("11. TESTE DE COMPATIBILIDADE CRUZADA (strict=True)")
print("=" * 70)

def test_load(model_cls, ckpt_dict, model_name, ckpt_name):
    m = model_cls()
    try:
        m.load_state_dict(ckpt_dict, strict=True)
        print(f"[PASSOU] {model_name} + {ckpt_name}: Carregado com sucesso sob strict=True!")
        return True
    except RuntimeError as e:
        err_msg = str(e).split("\n")[0]
        print(f"[FALHOU] {model_name} + {ckpt_name}: RuntimeError ({err_msg})")
        return False

test_load(PSHDR, sd_ps, "PSHDR", "PSHDR_G.pth")
test_load(SAFHDR, sd_saf, "SAFHDR", "model_tm_406392_G.pth")
test_load(PSHDR, sd_saf, "PSHDR", "model_tm_406392_G.pth")
test_load(SAFHDR, sd_ps, "SAFHDR", "PSHDR_G.pth")

print("\n" + "=" * 70)
print("12. VERIFIQUE params VS params_ema")
print("=" * 70)
print("PSHDR checkpoint:")
print("  'params' in ckpt    :", "params" in sd_ps_raw)
print("  'params_ema' in ckpt:", "params_ema" in sd_ps_raw)

print("SAFHDR checkpoint:")
print("  'params' in ckpt    :", "params" in sd_saf_raw)
print("  'params_ema' in ckpt:", "params_ema" in sd_saf_raw)

if "params" in sd_ps_raw and "params_ema" in sd_ps_raw:
    eq = all(torch.equal(sd_ps_raw["params"][k], sd_ps_raw["params_ema"][k]) for k in sd_ps_raw["params"])
    print("  PSHDR params == params_ema?", eq)

if "params" in sd_saf_raw and "params_ema" in sd_saf_raw:
    eq = all(torch.equal(sd_saf_raw["params"][k], sd_saf_raw["params_ema"][k]) for k in sd_saf_raw["params"])
    print("  SAFHDR params == params_ema?", eq)
