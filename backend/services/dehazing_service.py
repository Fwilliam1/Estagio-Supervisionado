import io
import time
import base64
import os
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np
from PIL import Image
import torch
import torch.nn.functional as F

from archs.depth_anything_v2.dpt import DepthAnythingV2
from archs.udpnet.fsnet_udpnet import FSNet, build_net
from .exceptions import ValidacaoError, ServiceException

BACKEND_DIR = Path(__file__).resolve().parent.parent
PRETRAINED_MODELS_DIR = BACKEND_DIR / "pretrained_models"


class DehazingService:
    """
    Servico para remocao de nevoa (Image Dehazing) utilizando pipeline em 2 etapas:
    1. Estimativa do Mapa de Profundidade via Depth Anything V2 (ViT-S).
    2. Dehazing guiado por profundidade via UDPNet (FSNet treinado no dataset OTS).
    """

    DEPTH_WEIGHTS_PATH = PRETRAINED_MODELS_DIR / "depth_anything_v2_vits.pth"
    DEHAZING_WEIGHTS_PATH = PRETRAINED_MODELS_DIR / "FSNet_UDPNet_OTS.ckpt"

    _depth_model: Optional[DepthAnythingV2] = None
    _dehazing_model: Optional[FSNet] = None
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
    def obter_modelo_profundidade(cls) -> DepthAnythingV2:
        """Carrega e retorna o modelo Depth Anything V2 (ViT-S) com cache em memoria."""
        if cls._depth_model is not None:
            return cls._depth_model

        if not os.path.exists(cls.DEPTH_WEIGHTS_PATH):
            raise ServiceException(
                f"Arquivo de pesos do Depth Anything V2 nao encontrado: {cls.DEPTH_WEIGHTS_PATH}"
            )

        device = cls.get_device()
        model = DepthAnythingV2(
            encoder='vits',
            features=64,
            out_channels=[48, 96, 192, 384]
        )
        state_dict = torch.load(cls.DEPTH_WEIGHTS_PATH, map_location='cpu')
        model.load_state_dict(state_dict, strict=True)
        model.to(device)
        model.eval()

        cls._depth_model = model
        return model

    @classmethod
    def obter_modelo_dehazing(cls) -> FSNet:
        """Carrega e retorna o modelo UDPNet (FSNet OTS) com cache em memoria."""
        if cls._dehazing_model is not None:
            return cls._dehazing_model

        if not os.path.exists(cls.DEHAZING_WEIGHTS_PATH):
            raise ServiceException(
                f"Arquivo de pesos do UDPNet (FSNet OTS) nao encontrado: {cls.DEHAZING_WEIGHTS_PATH}"
            )

        device = cls.get_device()
        model = build_net()

        checkpoint = torch.load(cls.DEHAZING_WEIGHTS_PATH, map_location='cpu', weights_only=False)
        raw_state_dict = checkpoint.get('state_dict', checkpoint) if isinstance(checkpoint, dict) else checkpoint

        # Remove o prefixo 'model.' das chaves geradas pelo PyTorch Lightning
        cleaned_state_dict = {
            k.replace('model.', ''): v for k, v in raw_state_dict.items()
        }

        model.load_state_dict(cleaned_state_dict, strict=True)
        model.to(device)
        model.eval()

        cls._dehazing_model = model
        return model

    @classmethod
    def processar_imagem_convir(
        cls,
        image_bytes: bytes,
        version: str = 'small'
    ) -> Dict[str, Any]:
        """
        Executa a inferência de Dehazing utilizando a arquitetura ConvIR (small, pesos ots_small.pkl).
        """
        from .convir_service import ConvIRService
        return ConvIRService.processar_imagem(image_bytes=image_bytes, version=version)

    @classmethod
    def processar_imagem(
        cls,
        image_bytes: bytes,
        input_size: int = 518,
        modelo: str = 'udpnet',
        version: str = 'small'
    ) -> Dict[str, Any]:
        """
        Executa o pipeline de Dehazing selecionado:
        - modelo='udpnet': Depth Anything V2 + UDPNet (FSNet OTS)
        - modelo='convir': ConvIR small (ots_small.pkl)
        """
        if modelo and str(modelo).lower() in ('convir', 'convir_small', 'convir-small', 'convir_ots'):
            return cls.processar_imagem_convir(image_bytes=image_bytes, version=version)

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

        device = cls.get_device()
        depth_model = cls.obter_modelo_profundidade()
        dehazing_model = cls.obter_modelo_dehazing()

        start_time = time.perf_counter()

        # 2. Etapa 1: Inferencia do Mapa de Profundidade via Depth Anything V2
        np_rgb = np.array(pil_image, dtype=np.uint8)
        np_bgr = np_rgb[:, :, ::-1].copy()

        try:
            depth_map = depth_model.infer_image(np_bgr, input_size=input_size)
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            cpu_depth = cls.obter_modelo_profundidade().to('cpu')
            depth_map = cpu_depth.infer_image(np_bgr, input_size=input_size)

        # Normaliza profundidade para [0.0, 1.0]
        d_min = float(depth_map.min())
        d_max = float(depth_map.max())
        denom = (d_max - d_min) if (d_max - d_min) > 1e-8 else 1.0
        depth_norm = (depth_map - d_min) / denom

        # 3. Etapa 2: Preparacao dos Tensores RGB + Profundidade (4 canais)
        tensor_rgb = torch.from_numpy(np_rgb).float().permute(2, 0, 1).unsqueeze(0) / 255.0
        tensor_depth = torch.from_numpy(depth_norm).float().unsqueeze(0).unsqueeze(0)

        # Concatena canais: [R, G, B, Depth]
        input_4ch = torch.cat([tensor_rgb, tensor_depth], dim=1).to(device)

        # 4. Padding para garantir dimensoes compativeis com janelas OCAB (multiplo de 16)
        h, w = input_4ch.shape[2], input_4ch.shape[3]
        factor = 16
        pad_h = (factor - h % factor) % factor
        pad_w = (factor - w % factor) % factor

        if pad_h > 0 or pad_w > 0:
            padded_input = F.pad(input_4ch, (0, pad_w, 0, pad_h), mode='reflect')
        else:
            padded_input = input_4ch

        # 5. Inferencia no UDPNet (FSNet OTS)
        try:
            with torch.no_grad():
                outputs = dehazing_model(padded_input)
                pred = outputs[2][:, :, :h, :w]
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            cpu_dehazing = cls.obter_modelo_dehazing().to('cpu')
            with torch.no_grad():
                outputs = cpu_dehazing(padded_input.to('cpu'))
                pred = outputs[2][:, :, :h, :w]

        elapsed_time = time.perf_counter() - start_time

        # 6. Pos-processamento e geracao da imagem final
        pred_clamped = torch.clamp(pred, 0.0, 1.0)
        output_np = (pred_clamped.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0).round().astype(np.uint8)

        result_pil = Image.fromarray(output_np)
        proc_w, proc_h = result_pil.size

        # 7. Exportacao da imagem final para PNG e Base64
        buffer = io.BytesIO()
        result_pil.save(buffer, format='PNG', optimize=True)
        processed_bytes = buffer.getvalue()

        b64_str = base64.b64encode(processed_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_str}"

        # Mapa de profundidade em escala de cinza para metadados opcionais
        depth_uint8 = (depth_norm * 255.0).clip(0, 255).astype(np.uint8)
        depth_pil = Image.fromarray(depth_uint8)
        depth_buf = io.BytesIO()
        depth_pil.save(depth_buf, format='PNG')
        depth_b64 = f"data:image/png;base64,{base64.b64encode(depth_buf.getvalue()).decode('utf-8')}"

        tamanho_original_kb = round(len(image_bytes) / 1024, 2)
        tamanho_processado_kb = round(len(processed_bytes) / 1024, 2)

        return {
            "imagem_processada_bytes": processed_bytes,
            "imagem_processada_base64": data_uri,
            "mapa_profundidade_base64": depth_b64,
            "largura_original": orig_w,
            "altura_original": orig_h,
            "resolucao_original": f"{orig_w}x{orig_h}",
            "largura_processada": proc_w,
            "altura_processada": proc_h,
            "resolucao_processada": f"{proc_w}x{proc_h}",
            "modelo_dehazing": "UDPNet_FSNet_OTS",
            "modelo_profundidade": "DepthAnythingV2_ViTS",
            "tempo_execucao_segundos": round(elapsed_time, 3),
            "tamanho_original_kb": tamanho_original_kb,
            "tamanho_processado_kb": tamanho_processado_kb,
            "dispositivo": str(device),
        }
