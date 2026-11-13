import os
import sys
import torch

sys.stdout.reconfigure(encoding="utf-8")
backend_dir = os.path.abspath(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from archs.hdrunet.UNet_arch import HDRUNet
from archs.safhdr.SAFHDR import HDRUNet as SAFHDR

hdrunet_ckpt = os.path.join(backend_dir, "pretrained_models", "pretrained_model.pth")
safhdr_ckpt = os.path.join(backend_dir, "pretrained_models", "model_tm_406392_G.pth")

# Instanciação e carga HDRUNet
m_hdrunet = HDRUNet()
sd_h = torch.load(hdrunet_ckpt, map_location="cpu", weights_only=True)
if isinstance(sd_h, dict) and "params" in sd_h:
    sd_h = sd_h["params"]
m_hdrunet.load_state_dict(sd_h, strict=True)
m_hdrunet.eval()

# Instanciação e carga SAFHDR
m_safhdr = SAFHDR()
sd_s = torch.load(safhdr_ckpt, map_location="cpu", weights_only=True)
if isinstance(sd_s, dict) and "params" in sd_s:
    sd_s = sd_s["params"]
m_safhdr.load_state_dict(sd_s, strict=True)
m_safhdr.eval()

params_h = sum(p.numel() for p in m_hdrunet.parameters())
params_s = sum(p.numel() for p in m_safhdr.parameters())

torch.manual_seed(42)
x = torch.rand(1, 3, 128, 128)

with torch.no_grad():
    out_h = m_hdrunet((x, x.clone()))
    out_s = m_safhdr(x)

mean_abs_diff = torch.mean(torch.abs(out_h - out_s)).item()
max_abs_diff = torch.max(torch.abs(out_h - out_s)).item()

print("========== HDRUNet ==========")
print(f"classe: {m_hdrunet.__class__.__module__}.{m_hdrunet.__class__.__name__}")
print(f"checkpoint: {hdrunet_ckpt}")
print(f"parâmetros: {params_h}")
print(f"saída: shape={list(out_h.shape)}, min={out_h.min().item():.4f}, max={out_h.max().item():.4f}, mean={out_h.mean().item():.4f}")
print()
print("========== SAFHDR ==========")
print(f"classe: {m_safhdr.__class__.__module__}.{m_safhdr.__class__.__name__}")
print(f"checkpoint: {safhdr_ckpt}")
print(f"parâmetros: {params_s}")
print(f"saída: shape={list(out_s.shape)}, min={out_s.min().item():.4f}, max={out_s.max().item():.4f}, mean={out_s.mean().item():.4f}")
print()
print("========== COMPARAÇÃO ==========")
print(f"arquiteturas diferentes: {'SIM' if params_h != params_s else 'NÃO'}")
print(f"checkpoints diferentes: {'SIM' if sd_h.keys() != sd_s.keys() else 'NÃO'}")
print(f"saídas diferentes: {'SIM' if mean_abs_diff > 1e-4 else 'NÃO'} (diff média={mean_abs_diff:.4f}, max={max_abs_diff:.4f})")
