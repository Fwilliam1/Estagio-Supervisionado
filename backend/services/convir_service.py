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

from archs.convir import ConvIR, build_net
from .exceptions import ValidacaoError, ServiceException

BACKEND_DIR = Path(__file__).resolve().parent.parent
PRETRAINED_MODELS_DIR = BACKEND_DIR / "pretrained_models"


class ConvIRService:
    """
    Serviço para restauração de imagens e remoção de névoa (Image Dehazing)
    utilizando a arquitetura convolucional ConvIR (Revitalizing Convolutional Network for Image Restoration).
    Utiliza o modelo versão 'small' e os pesos 'ots_small.pkl' treinados no dataset RESIDE-OTS.
    """

    WEIGHTS_PATH = PRETRAINED_MODELS_DIR / "ots_small.pkl"
    ALT_WEIGHTS_PATH = PRETRAINED_MODELS_DIR / "ots-small.pkl"

    _model: Optional[ConvIR] = None
    _device: Optional[torch.device] = None

    @classmethod
    def get_device(cls) -> torch.device:
        """Determina o dispositivo de execução (CUDA se disponível, senão CPU)."""
        if cls._device is None:
            if torch.cuda.is_available():
                cls._device = torch.device('cuda')
            else:
                cls._device = torch.device('cpu')
        return cls._device

    @classmethod
    def obter_caminho_pesos(cls) -> Path:
        """Retorna o caminho válido do arquivo de pesos do modelo ConvIR small."""
        if cls.WEIGHTS_PATH.exists():
            return cls.WEIGHTS_PATH
        if cls.ALT_WEIGHTS_PATH.exists():
            return cls.ALT_WEIGHTS_PATH
        raise ServiceException(
            f"Arquivo de pesos do ConvIR não encontrado em {cls.WEIGHTS_PATH} ou {cls.ALT_WEIGHTS_PATH}."
        )

    @classmethod
    def obter_modelo(cls, version: str = 'small') -> ConvIR:
        """Carrega e retorna o modelo ConvIR com cache em memória."""
        if cls._model is not None:
            return cls._model

        weights_path = cls.obter_caminho_pesos()
        device = cls.get_device()

        model = build_net(version=version)
        checkpoint = torch.load(weights_path, map_location='cpu', weights_only=False)
        state_dict = checkpoint.get('model', checkpoint) if isinstance(checkpoint, dict) else checkpoint

        model.load_state_dict(state_dict, strict=True)
        model.to(device)
        model.eval()

        cls._model = model
        return model

    @classmethod
    def processar_imagem(
        cls,
        image_bytes: bytes,
        version: str = 'small'
    ) -> Dict[str, Any]:
        """
        Executa a inferência de Dehazing utilizando o modelo ConvIR (small, pesos ots_small.pkl).

        Args:
            image_bytes: Bytes da imagem codificada (PNG/JPEG/etc.).
            version: Versão do modelo ConvIR ('small').

        Returns:
            Dict com a imagem processada (bytes e base64), dimensões e metadados.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValidacaoError("Nenhum dado de imagem foi enviado.")

        # 1. Leitura e validação da imagem
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            raise ValidacaoError(f"Formato de imagem inválido ou corrompido: {str(e)}")

        orig_w, orig_h = pil_image.size
        if orig_w > 4096 or orig_h > 4096:
            raise ValidacaoError(
                f"A resolução da imagem ({orig_w}x{orig_h}) excede o limite máximo permitido (4096x4096)."
            )

        device = cls.get_device()
        model = cls.obter_modelo(version=version)

        start_time = time.perf_counter()

        # 2. Conversão da imagem para tensor PyTorch [1, 3, H, W] normalizado em [0.0, 1.0]
        np_rgb = np.array(pil_image, dtype=np.float32) / 255.0
        tensor_rgb = torch.from_numpy(np_rgb).permute(2, 0, 1).unsqueeze(0).to(device)

        # 3. Padding para garantir que a resolução seja múltipla de 32 e >= 256
        # A arquitetura do ConvIR realiza 2 downsamplings (fator 4) e pooling de até 8 com dilatações até 11
        # Dimensão mínima 256 evita que o pooling interno reduza o tensor abaixo do tamanho da dilatação
        h, w = tensor_rgb.shape[2], tensor_rgb.shape[3]
        factor = 32
        min_size = 256
        target_h = max(min_size, ((h + factor - 1) // factor) * factor)
        target_w = max(min_size, ((w + factor - 1) // factor) * factor)

        pad_h = target_h - h
        pad_w = target_w - w

        # Se o padding for menor que a dimensão original, usa 'reflect'; caso contrário 'replicate'
        pad_mode = 'reflect' if (pad_h < h and pad_w < w) else 'replicate'
        if pad_h > 0 or pad_w > 0:
            padded_input = F.pad(tensor_rgb, (0, pad_w, 0, pad_h), mode=pad_mode)
        else:
            padded_input = tensor_rgb

        # 4. Inferência no ConvIR
        try:
            with torch.no_grad():
                outputs = model(padded_input)
                # outputs[2] corresponde à saída em escala total (1/1)
                pred = outputs[2][:, :, :h, :w]
        except torch.cuda.OutOfMemoryError:
            torch.cuda.empty_cache()
            cpu_model = cls.obter_modelo(version=version).to('cpu')
            with torch.no_grad():
                outputs = cpu_model(padded_input.to('cpu'))
                pred = outputs[2][:, :, :h, :w]

        elapsed_time = time.perf_counter() - start_time

        # 5. Pós-processamento: recorte dos valores para [0.0, 1.0] e conversão para uint8
        pred_clamped = torch.clamp(pred, 0.0, 1.0)
        output_np = (pred_clamped.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255.0).round().astype(np.uint8)

        result_pil = Image.fromarray(output_np)
        proc_w, proc_h = result_pil.size

        # 6. Exportação para PNG e Base64
        buffer = io.BytesIO()
        result_pil.save(buffer, format='PNG', optimize=True)
        processed_bytes = buffer.getvalue()

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
            "modelo_dehazing": f"ConvIR_{version}_OTS",
            "pesos": "ots_small.pkl",
            "versao": version,
            "tempo_execucao_segundos": round(elapsed_time, 3),
            "tamanho_original_kb": tamanho_original_kb,
            "tamanho_processado_kb": tamanho_processado_kb,
            "dispositivo": str(device),
        }
