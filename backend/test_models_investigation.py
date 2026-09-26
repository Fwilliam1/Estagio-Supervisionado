import os
import sys
import torch

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "backend")))

from archs.pshdr.PSHDR import HDRUNet as PSHDR
from archs.safhdr.SAFHDR import HDRUNet as SAFHDR

pshdr_ckpt = os.path.abspath("backend/pretrained_models/PSHDR_G.pth")
safhdr_ckpt = os.path.abspath("backend/pretrained_models/model_tm_406392_G.pth")

# Instanciação e carga PSHDR
m_pshdr = PSHDR()
sd_p = torch.load(pshdr_ckpt, map_location="cpu")
if "params" in sd_p:
    sd_p = sd_p["params"]
m_pshdr.load_state_dict(sd_p, strict=True)
m_pshdr.eval()

# Instanciação e carga SAFHDR
m_safhdr = SAFHDR()
sd_s = torch.load(safhdr_ckpt, map_location="cpu")
if "params" in sd_s:
    sd_s = sd_s["params"]
m_safhdr.load_state_dict(sd_s, strict=True)
m_safhdr.eval()

params_p = sum(p.numel() for p in m_pshdr.parameters())
params_s = sum(p.numel() for p in m_safhdr.parameters())

torch.manual_seed(42)
x = torch.rand(1, 3, 128, 128)

with torch.no_grad():
    out_p = m_pshdr(x)
    out_s = m_safhdr(x)

mean_abs_diff = torch.mean(torch.abs(out_p - out_s)).item()
max_abs_diff = torch.max(torch.abs(out_p - out_s)).item()

print("========== PSHDR ==========")
print(f"classe: {m_pshdr.__class__.__module__}.{m_pshdr.__class__.__name__}")
print(f"checkpoint: {pshdr_ckpt}")
print(f"parâmetros: {params_p}")
print(f"saída: shape={list(out_p.shape)}, min={out_p.min().item():.4f}, max={out_p.max().item():.4f}, mean={out_p.mean().item():.4f}")
print()
print("========== SAFHDR ==========")
print(f"classe: {m_safhdr.__class__.__module__}.{m_safhdr.__class__.__name__}")
print(f"checkpoint: {safhdr_ckpt}")
print(f"parâmetros: {params_s}")
print(f"saída: shape={list(out_s.shape)}, min={out_s.min().item():.4f}, max={out_s.max().item():.4f}, mean={out_s.mean().item():.4f}")
print()
print("========== COMPARAÇÃO ==========")
print(f"arquiteturas diferentes: {'SIM' if params_p != params_s else 'NÃO'}")
print(f"checkpoints diferentes: {'SIM' if sd_p.keys() != sd_s.keys() else 'NÃO'}")
print(f"saídas diferentes: {'SIM' if mean_abs_diff > 1e-4 else 'NÃO'} (diff média={mean_abs_diff:.4f}, max={max_abs_diff:.4f})")
