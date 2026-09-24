import io
import time
import base64
from typing import Dict, Any, Optional
from pathlib import Path
import numpy as np
from PIL import Image
import cv2

import math
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms

from .exceptions import ValidacaoError, ServiceException

import sys
backend_dir = str(Path(__file__).resolve().parent.parent)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from archs.safhdr.SAFHDR import HDRUNet as SAFHDR
from archs.pshdr.PSHDR import HDRUNet as PSHDR


class HdrService_VersãoFELIPEEEmanuel:
    """
    Serviço para aprimoramento de alcance dinâmico (HDR / Tone Mapping).
    Aplica equalização adaptativa de contraste com limite de contraste (CLAHE) no espaço de cor LAB,
    realce de detalhes locais e balanço de exposição para altas luzes e sombras.
    """

    @classmethod
    def processar_imagem(cls, image_bytes: bytes, clip_limit: float = 2.5, tile_grid_size: int = 8) -> Dict[str, Any]:
        """
        Processa os bytes da imagem aplicando algoritmo HDR / Tone Mapping de faixa dinâmica estendida.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValidacaoError("Os dados da imagem estão vazios.")

        start_time = time.perf_counter()

        # 1. Carrega a imagem via PIL e converte para array NumPy RGB
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
        except Exception as e:
            raise ValidacaoError(f"Formato de imagem inválido ou corrompido: {str(e)}")

        orig_w, orig_h = pil_image.size
        img_np = np.array(pil_image)

        # 2. Conversão para espaço de cor LAB para desacoplar luminância e crominância
        # BGR para OpenCV
        bgr = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # 3. Aplica CLAHE no canal L (Luminância) para equalizar contraste adaptativamente
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
        l_enhanced = clahe.apply(l_channel)

        # 4. Fusão e suavização de sombras com curva de gama suave
        l_float = l_enhanced.astype(np.float32) / 255.0
        # Curva de tom suave para elevar sombras sem estourar altas luzes
        l_gamma = np.power(l_float, 0.9)
        l_final = np.clip(l_gamma * 255.0, 0, 255).astype(np.uint8)

        # 5. Realce sutil de vibração de cores nos canais A e B
        a_float = a_channel.astype(np.float32) - 128.0
        b_float = b_channel.astype(np.float32) - 128.0
        a_boost = np.clip(a_float * 1.08 + 128.0, 0, 255).astype(np.uint8)
        b_boost = np.clip(b_float * 1.08 + 128.0, 0, 255).astype(np.uint8)

        merged_lab = cv2.merge((l_final, a_boost, b_boost))
        bgr_enhanced = cv2.cvtColor(merged_lab, cv2.COLOR_LAB2BGR)

        # 6. Realce de detalhes finos (Unsharp Masking suave)
        gaussian = cv2.GaussianBlur(bgr_enhanced, (0, 0), 2.0)
        unsharp = cv2.addWeighted(bgr_enhanced, 1.25, gaussian, -0.25, 0)
        unsharp = np.clip(unsharp, 0, 255).astype(np.uint8)

        rgb_result = cv2.cvtColor(unsharp, cv2.COLOR_BGR2RGB)
        result_pil = Image.fromarray(rgb_result)
        proc_w, proc_h = result_pil.size

        elapsed_time = time.perf_counter() - start_time

        # 7. Serialização para PNG e Base64
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
            "modelo": "HDR_ToneMapping_CLAHE",
            "tempo_execucao_segundos": round(elapsed_time, 3),
            "tamanho_original_kb": tamanho_original_kb,
            "tamanho_processado_kb": tamanho_processado_kb,
            "dispositivo": "CPU",
        }


class HDRService:
    # Modelos carregados em cache (Lazy Loading) e dispositivo
    _models: Dict[str, nn.Module] = {}
    _device: Optional[torch.device] = None

    @classmethod
    def get_device(cls) -> torch.device:
        """Determina o dispositivo de execução (CUDA se disponível, senão CPU)."""
        if cls._device is None:
            cls._device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        return cls._device

    @classmethod
    def normalizar_nome_modelo(cls, model_name: Optional[str]) -> str:
        """Normaliza o nome do modelo para 'PSHDR' ou 'SAFHDR'."""
        nome = str(model_name or 'PSHDR').strip().upper()
        if 'SAF' in nome:
            return 'SAFHDR'
        return 'PSHDR'

    @classmethod
    def _carregar_modelo(cls, model_name: str = 'PSHDR') -> nn.Module:
        """Carrega o modelo e os pesos apenas se ainda não estiverem na memória (Lazy Loading)."""
        modelo_chave = cls.normalizar_nome_modelo(model_name)
        if modelo_chave not in cls._models or cls._models[modelo_chave] is None:
            device = cls.get_device()
            base_dir = Path(__file__).resolve().parent.parent

            if modelo_chave == 'PSHDR':
                instancia = PSHDR().to(device)
                caminho_peso = base_dir / "pretrained_models" / "PSHDR_G.pth"
                if not caminho_peso.exists():
                    fallback = Path(r".\backend\pretrained_models\PSHDR_G.pth")
                    if fallback.exists():
                        caminho_peso = fallback
                    else:
                        raise ServiceException(
                            f"Pesos do modelo PSHDR não encontrados em: {caminho_peso}. "
                            "Certifique-se de que o arquivo 'PSHDR_G.pth' está na pasta 'backend/pretrained_models/'.",
                            status_code=500
                        )
            else:
                instancia = SAFHDR().to(device)
                caminho_peso = base_dir / "pretrained_models" / "model_tm_406392_G.pth"
                if not caminho_peso.exists():
                    fallback = Path(r".\backend\pretrained_models\model_tm_406392_G.pth")
                    if fallback.exists():
                        caminho_peso = fallback
                    else:
                        raise ServiceException(
                            f"Pesos do modelo SAFHDR não encontrados em: {caminho_peso}. "
                            "Certifique-se de que o arquivo 'model_tm_406392_G.pth' está na pasta 'backend/pretrained_models/'.",
                            status_code=500
                        )

            state_dict = torch.load(str(caminho_peso), map_location=device, weights_only=True)

            if 'params_ema' in state_dict:
                instancia.load_state_dict(state_dict['params_ema'], strict=True)
            elif 'params' in state_dict:
                instancia.load_state_dict(state_dict['params'], strict=True)
            else:
                instancia.load_state_dict(state_dict, strict=True)

            instancia.eval()
            cls._models[modelo_chave] = instancia

        return cls._models[modelo_chave]

    # Propriedade de retrocompatibilidade
    @classmethod
    @property
    def model(cls):
        return cls._models.get('SAFHDR') or cls._models.get('PSHDR')

    @classmethod
    def _pre_processar_hdr(cls, hdr_tensor: torch.Tensor) -> np.ndarray:
        """Remove batch, converte Tensor (C, H, W) RGB para NumPy (H, W, C) BGR e garante float32."""
        if hdr_tensor.dim() == 4:
            hdr_tensor = hdr_tensor.squeeze(0)

        hdr_np = hdr_tensor.detach().cpu().numpy()
        hdr_np = np.transpose(hdr_np, (1, 2, 0))
        hdr_np = np.nan_to_num(hdr_np, nan=0.0, posinf=1.0, neginf=0.0)
        hdr_np = np.float32(np.clip(hdr_np, 0.0, None))

        return cv2.cvtColor(hdr_np, cv2.COLOR_RGB2BGR)

    @classmethod
    def _pos_processar_ldr(cls, ldr_bgr: np.ndarray) -> torch.Tensor:
        """Converte BGR para RGB, reordena para (C, H, W) e retorna Tensor clampeado [0.0, 1.0]."""
        ldr_bgr = np.nan_to_num(ldr_bgr, nan=0.0, posinf=1.0, neginf=0.0)
        ldr_bgr = np.clip(ldr_bgr, 0.0, 1.0)
        ldr_rgb = cv2.cvtColor(ldr_bgr, cv2.COLOR_BGR2RGB)
        ldr_tensor = torch.from_numpy(np.transpose(ldr_rgb, (2, 0, 1)))
        return torch.clamp(ldr_tensor, 0.0, 1.0)

    @classmethod
    def aplicar_tone_mapping_drago_cv2(
        cls, 
        hdr_tensor: torch.Tensor, 
        gamma: float = 2.2, 
        saturation: float = 1.0, 
        bias: float = 1.0
    ) -> torch.Tensor:
        """Aplica o Tone Mapping de Drago usando o OpenCV."""
        hdr_bgr = cls._pre_processar_hdr(hdr_tensor)
        tonemap = cv2.createTonemapDrago(
            gamma=gamma, 
            saturation=saturation, 
            bias=bias
        )
        ldr_bgr = tonemap.process(hdr_bgr)
        return cls._pos_processar_ldr(ldr_bgr)

    @classmethod
    def aplicar_tone_mapping_reinhard_cv2(
        cls, 
        hdr_tensor: torch.Tensor, 
        gamma: float = 1.0, 
        intensity: float = 0.0, 
        light_adapt: float = 0.0, 
        color_adapt: float = 1.0
    ) -> torch.Tensor:
        """Aplica o Tone Mapping de Reinhard usando o OpenCV."""
        hdr_bgr = cls._pre_processar_hdr(hdr_tensor)
        tonemap = cv2.createTonemapReinhard(
            gamma=gamma, 
            intensity=intensity, 
            light_adapt=light_adapt, 
            color_adapt=color_adapt
        )
        ldr_bgr = tonemap.process(hdr_bgr)
        return cls._pos_processar_ldr(ldr_bgr)

    @classmethod
    def aplicar_tone_mapping_mantiuk_cv2(
        cls, 
        hdr_tensor: torch.Tensor, 
        gamma: float = 2.2, 
        scale: float = 0.7, 
        saturation: float = 1.0
    ) -> torch.Tensor:
        """Aplica o Tone Mapping de Mantiuk usando o OpenCV."""
        hdr_bgr = cls._pre_processar_hdr(hdr_tensor)
        tonemap = cv2.createTonemapMantiuk(
            gamma=gamma, 
            scale=scale, 
            saturation=saturation
        )
        ldr_bgr = tonemap.process(hdr_bgr)
        return cls._pos_processar_ldr(ldr_bgr)

    @classmethod
    def aplicar_tone_mapping_logaritmico(
        cls, hdr_tensor: torch.Tensor, mu: float = 5000.0
    ) -> torch.Tensor:
        """Aplica o Tone Mapping Logarítmico (mu-law) isoladamente a um tensor em GPU/CPU."""
        # Garante que não existam valores negativos
        hdr_tensor = torch.clamp(hdr_tensor, min=0.0)

        # Aplica a fórmula mu-law
        tonemapped_tensor = torch.log(1.0 + mu * hdr_tensor) / math.log(
            1.0 + mu
        )

        # Garante que os valores fiquem entre 0.0 e 1.0
        return torch.clamp(tonemapped_tensor, 0.0, 1.0)

    # Alias de compatibilidade
    aplicar_tone_mapping = aplicar_tone_mapping_logaritmico

    @classmethod
    def processar_imagem(
        cls, 
        image_bytes: bytes, 
        clip_limit: float = 2.5, 
        tile_grid_size: int = 8,
        tone_mapping: str = 'reinhard',
        model_name: str = 'PSHDR'
    ) -> Dict[str, Any]:
        """
        Processa os bytes da imagem aplicando algoritmo HDR (PSHDR ou SAFHDR), passando pelo modelo
        e aplicando um dos 4 operadores de tone mapping (Reinhard, Drago, Mantiuk, Logarítmico).
        Garante padding para que qualquer dimensão de imagem seja processada sem incompatibilidade de tensores.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValidacaoError("Os dados da imagem estão vazios.")

        start_time = time.perf_counter()

        # 1. Garante que o modelo desejado está carregado antes de processar
        modelo_norm = cls.normalizar_nome_modelo(model_name)
        modelo_instancia = cls._carregar_modelo(modelo_norm)
        device = cls.get_device()

        # 2. Carrega a imagem e converte para tensor
        try:
            pil_image = Image.open(io.BytesIO(image_bytes))
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
        except Exception as e:
            raise ValidacaoError(f"Formato de imagem inválido ou corrompido: {str(e)}")

        orig_w, orig_h = pil_image.size
        tensor_img = transforms.ToTensor()(pil_image).unsqueeze(0).to(device)

        # 3. Padding para garantir que a resolução seja múltipla de 16
        factor = 16
        pad_h = (factor - orig_h % factor) % factor
        pad_w = (factor - orig_w % factor) % factor

        if pad_h > 0 or pad_w > 0:
            pad_mode = 'reflect' if (pad_h < orig_h and pad_w < orig_w) else 'replicate'
            padded_input = F.pad(tensor_img, (0, pad_w, 0, pad_h), mode=pad_mode)
        else:
            padded_input = tensor_img

        # 4. Passa pelo modelo inferindo sem gradiente
        with torch.no_grad():
            output_padded = modelo_instancia(padded_input)

        # Corta o padding excedente para retornar o tamanho original exato
        output = output_padded[:, :, :orig_h, :orig_w]

        # 5. Aplica o Tone Mapping selecionado entre os 4 disponíveis
        tm_key = str(tone_mapping or 'reinhard').strip().lower()
        if 'drago' in tm_key:
            tonemapped_tensor = cls.aplicar_tone_mapping_drago_cv2(output)
            tm_nome = 'Drago'
        elif 'mantiuk' in tm_key:
            tonemapped_tensor = cls.aplicar_tone_mapping_mantiuk_cv2(output)
            tm_nome = 'Mantiuk'
        elif 'log' in tm_key or 'mu' in tm_key:
            tonemapped_tensor = cls.aplicar_tone_mapping_logaritmico(output)
            tm_nome = 'Logarítmico'
        else:
            tonemapped_tensor = cls.aplicar_tone_mapping_reinhard_cv2(output)
            tm_nome = 'Reinhard'

        # 6. Converte para PIL (garante CPU e formato C, H, W)
        if tonemapped_tensor.dim() == 4:
            tonemapped_tensor = tonemapped_tensor.squeeze(0)
        tonemapped_tensor = tonemapped_tensor.detach().cpu()
        imagem_final_pil = transforms.ToPILImage()(tonemapped_tensor)
        proc_w, proc_h = imagem_final_pil.size

        elapsed_time = time.perf_counter() - start_time

        # 7. Serialização para bytes e base64 data-uri
        buffer = io.BytesIO()
        imagem_final_pil.save(buffer, format='PNG', optimize=True)
        processed_bytes = buffer.getvalue()

        b64_str = base64.b64encode(processed_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_str}"

        tamanho_original_kb = round(len(image_bytes) / 1024, 2)
        tamanho_processado_kb = round(len(processed_bytes) / 1024, 2)

        return {
            "imagem_tonemapped": imagem_final_pil,
            "imagem_processada_bytes": processed_bytes,
            "imagem_processada_base64": data_uri,
            "dimensoes_originais": (orig_w, orig_h),
            "largura_original": orig_w,
            "altura_original": orig_h,
            "resolucao_original": f"{orig_w}x{orig_h}",
            "largura_processada": proc_w,
            "altura_processada": proc_h,
            "resolucao_processada": f"{proc_w}x{proc_h}",
            "modelo": f"{modelo_norm} ({tm_nome})",
            "modelo_hdr": modelo_norm,
            "tone_mapping": tm_nome,
            "tempo_processamento": round(elapsed_time, 3),
            "tempo_execucao_segundos": round(elapsed_time, 3),
            "tamanho_original_kb": tamanho_original_kb,
            "tamanho_processado_kb": tamanho_processado_kb,
            "dispositivo": "CUDA" if device.type == "cuda" else "CPU",
        }