import io
import time
import base64
import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image
import torch
import matplotlib

from archs.depth_anything_v2.dpt import DepthAnythingV2
from .exceptions import ValidacaoError, ServiceException

BACKEND_DIR = Path(__file__).resolve().parent.parent
PRETRAINED_MODELS_DIR = BACKEND_DIR / "pretrained_models"


class DepthAnythingService:
    """
    Servico para inferencia e geracao de mapas de profundidade utilizando o modelo
    Depth Anything V2 (DINOv2 + DPT).
    Suporta encoders: 'vits' (Small - padrao rapido), 'vitb' (Base), 'vitl' (Large).
    """

    MODEL_CONFIGS = {
        'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
        'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
        'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]},
    }

    MODEL_WEIGHTS = {
        'vits': PRETRAINED_MODELS_DIR / "depth_anything_v2_vits.pth",
        'vitb': PRETRAINED_MODELS_DIR / "depth_anything_v2_vitb.pth",
        'vitl': PRETRAINED_MODELS_DIR / "depth_anything_v2_vitl.pth",
    }

    _models_cache: Dict[str, DepthAnythingV2] = {}
    _device: Optional[torch.device] = None

    @classmethod
    def get_device(cls) -> torch.device:
        """Determina o dispositivo de execucao (CUDA se disponivel, senao CPU)."""
        if cls._device is None:
            if torch.cuda.is_available():
                cls._device = torch.device('cuda')
            else:
                cls._device = torch.device('cpu')
        return cls._device

    @classmethod
    def obter_modelo(cls, encoder: str = 'vits') -> DepthAnythingV2:
        """
        Carrega o modelo Depth Anything V2 com os pesos pre-treinados correspondentes.
        Utiliza cache em memoria para evitar recarregamento repetido do disco.
        """
        encoder = (encoder or 'vits').lower().strip()
        if encoder not in cls.MODEL_CONFIGS:
            encoder = 'vits'

        if encoder in cls._models_cache:
            return cls._models_cache[encoder]

        weights_path = cls.MODEL_WEIGHTS.get(encoder)
        if not weights_path or not os.path.exists(weights_path):
            # Fallback para vits caso o peso especifico nao exista
            if encoder != 'vits' and os.path.exists(cls.MODEL_WEIGHTS['vits']):
                encoder = 'vits'
                weights_path = cls.MODEL_WEIGHTS['vits']
            else:
                raise ServiceException(
                    f"Arquivo de pesos do Depth Anything V2 nao encontrado: {weights_path}"
                )

        device = cls.get_device()
        config = cls.MODEL_CONFIGS[encoder]

        model = DepthAnythingV2(**config)
        state_dict = torch.load(weights_path, map_location='cpu')
        model.load_state_dict(state_dict, strict=True)
        model.to(device)
        model.eval()

        cls._models_cache[encoder] = model
        return model

    @classmethod
    def processar_imagem(
        cls,
        image_bytes: bytes,
        encoder: str = 'vits',
        grayscale: bool = True,
        colormap: str = 'Spectral_r',
        input_size: int = 518
    ) -> Dict[str, Any]:
        """
        Gera o mapa de profundidade a partir da imagem enviada em bytes.
        Retorna a imagem processada em PNG, Base64 e metadados completos.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValidacaoError("Nenhum dado de imagem foi enviado.")

        # 1. Leitura e validacao da imagem
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            raise ValidacaoError(f"Formato de imagem invalido ou corrompido: {str(e)}")

        orig_w, orig_h = pil_image.size
        if orig_w > 4096 or orig_h > 4096:
            raise ValidacaoError(
                f"A resolucao da imagem ({orig_w}x{orig_h}) excede o limite maximo permitido (4096x4096)."
            )

        # 2. Converte imagem para array NumPy (RGB -> BGR conforme esperado por OpenCV no DPT)
        np_rgb = np.array(pil_image, dtype=np.uint8)
        np_bgr = np_rgb[:, :, ::-1].copy()

        device = cls.get_device()
        model = cls.obter_modelo(encoder)

        start_time = time.perf_counter()

        # 3. Inferencia de profundidade
        try:
            depth_map = model.infer_image(np_bgr, input_size=input_size)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            cpu_model = cls.obter_modelo(encoder).to('cpu')
            depth_map = cpu_model.infer_image(np_bgr, input_size=input_size)

        elapsed_time = time.perf_counter() - start_time

        # 4. Normalizacao do mapa de profundidade para [0, 255] uint8
        d_min = float(depth_map.min())
        d_max = float(depth_map.max())
        denom = (d_max - d_min) if (d_max - d_min) > 1e-8 else 1.0
        depth_norm = ((depth_map - d_min) / denom * 255.0).clip(0, 255).astype(np.uint8)

        # 5. Formatacao visual (Escala de cinza ou Colormap)
        if grayscale:
            depth_rgb = np.repeat(depth_norm[..., np.newaxis], 3, axis=-1)
        else:
            try:
                cmap_obj = matplotlib.colormaps.get_cmap(colormap or 'Spectral_r')
                colored = cmap_obj(depth_norm)[:, :, :3]
                depth_rgb = (colored * 255.0).astype(np.uint8)
            except Exception:
                depth_rgb = np.repeat(depth_norm[..., np.newaxis], 3, axis=-1)

        result_pil = Image.fromarray(depth_rgb)
        proc_w, proc_h = result_pil.size

        # 6. Exportacao para PNG em memoria
        buffer = io.BytesIO()
        result_pil.save(buffer, format='PNG', optimize=True)
        processed_bytes = buffer.getvalue()

        # 7. Codificacao Base64
        b64_str = base64.b64encode(processed_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_str}"

        tamanho_original_kb = round(len(image_bytes) / 1024, 2)
        tamanho_processado_kb = round(len(processed_bytes) / 1024, 2)

        return {
            "imagem_processada_bytes": processed_bytes,
            "imagem_processada_base64": data_uri,
            "largura_original": orig_w,
            "altura_original": orig_h,
            "resolucao_original": f"{orig_w}x{orig_h}",
            "largura_processada": proc_w,
            "altura_processada": proc_h,
            "resolucao_processada": f"{proc_w}x{proc_h}",
            "encoder": encoder,
            "profundidade_min": round(d_min, 4),
            "profundidade_max": round(d_max, 4),
            "tempo_execucao_segundos": round(elapsed_time, 3),
            "tamanho_original_kb": tamanho_original_kb,
            "tamanho_processado_kb": tamanho_processado_kb,
            "dispositivo": str(device),
        }
