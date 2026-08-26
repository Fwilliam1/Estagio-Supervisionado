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
from archs.esc_arch import ESC
from .exceptions import ValidacaoError, ServiceException

# Diretório base do backend
BACKEND_DIR = Path(__file__).resolve().parent.parent
PRETRAINED_MODELS_DIR = BACKEND_DIR / "pretrained_models"


class SuperResolutionService:
    """
    Serviço para inferência de Super-Resolução utilizando a rede neural ESC
    (Efficient Super-Resolution with Convolution and Selective Self-Attention).
    100% autocontido no repositório com pesos locais para escalas x2, x3 e x4.
    """

    # Modelos e pesos relativos ao projeto
    MODEL_WEIGHTS = {
        2: PRETRAINED_MODELS_DIR / "ESC_DIV2K_X2.pth",
        3: PRETRAINED_MODELS_DIR / "ESC_DIV2K_X3.pth",
        4: PRETRAINED_MODELS_DIR / "ESC_DIV2K_X4.pth",
    }

    # Cache de modelos instanciados em memória
    _models_cache: Dict[int, ESC] = {}
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
    def obter_modelo(cls, scale: int = 2) -> ESC:
        """
        Carrega o modelo ESC com os pesos pré-treinados correspondentes à escala especificada.
        Utiliza cache em memória para evitar recarregamento repetido do disco.
        """
        scale = int(scale)
        if scale not in cls.MODEL_WEIGHTS:
            raise ValidacaoError(f"Fator de escala inválido: {scale}. As escalas suportadas são 2, 3 e 4.")

        if scale in cls._models_cache:
            return cls._models_cache[scale]

        weights_path = cls.MODEL_WEIGHTS[scale]
        if not os.path.exists(weights_path):
            raise ServiceException(f"Arquivo de pesos não encontrado no caminho: {weights_path}")

        device = cls.get_device()

        # Configuração da arquitetura ESC conforme especificações oficiais
        model = ESC(
            dim=64,
            pdim=16,
            kernel_size=13,
            n_blocks=5,
            conv_blocks=5,
            window_size=32,
            num_heads=4,
            upscaling_factor=scale,
            exp_ratio=1.25,
            attn_type='SDPA'
        )

        checkpoint = torch.load(weights_path, map_location='cpu')
        if isinstance(checkpoint, dict):
            state_dict = checkpoint.get('params_ema', checkpoint.get('params', checkpoint))
        else:
            state_dict = checkpoint

        model.load_state_dict(state_dict, strict=True)
        model.to(device)
        model.eval()

        cls._models_cache[scale] = model
        return model

    @classmethod
    def _processar_tensor_com_padding(cls, model: ESC, input_tensor: torch.Tensor, scale: int) -> torch.Tensor:
        """
        Executa a inferência do modelo garantindo que as dimensões H e W
        sejam múltiplos de window_size (32) via padding reflexivo.
        """
        _, _, h, w = input_tensor.shape
        window_size = 32

        pad_h = (window_size - h % window_size) % window_size
        pad_w = (window_size - w % window_size) % window_size

        if pad_h > 0 or pad_w > 0:
            padded_input = F.pad(input_tensor, (0, pad_w, 0, pad_h), mode='reflect')
        else:
            padded_input = input_tensor

        with torch.no_grad():
            output_padded = model(padded_input)

        out_h = h * scale
        out_w = w * scale
        output = output_padded[:, :, :out_h, :out_w]
        return output

    @classmethod
    def processar_imagem(
        cls,
        image_bytes: bytes,
        scale: int = 2
    ) -> Dict[str, Any]:
        """
        Recebe os bytes de uma imagem, aplica o algoritmo ESC Super-Resolution
        e retorna a imagem processada em PNG e Base64 juntamente com metadados.
        """
        if not image_bytes or len(image_bytes) == 0:
            raise ValidacaoError("Nenhum dado de imagem foi enviado.")

        scale = int(scale)
        if scale not in (2, 3, 4):
            raise ValidacaoError("O fator de escala deve ser 2, 3 ou 4.")

        # 1. Leitura e validação da imagem de entrada
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
        except Exception as e:
            raise ValidacaoError(f"Formato de imagem inválido ou arquivo corrompido: {str(e)}")

        orig_w, orig_h = pil_image.size

        if orig_w > 4096 or orig_h > 4096:
            raise ValidacaoError(f"A resolução da imagem ({orig_w}x{orig_h}) excede o limite máximo permitido (4096x4096).")

        device = cls.get_device()
        model = cls.obter_modelo(scale)

        # 2. Conversão da imagem para Tensor PyTorch normalizado [0, 1] no formato (1, 3, H, W)
        np_img = np.array(pil_image, dtype=np.float32) / 255.0
        tensor_img = torch.from_numpy(np_img).permute(2, 0, 1).unsqueeze(0).to(device)

        start_time = time.perf_counter()

        # 3. Inferência através da rede neural ESC
        try:
            output_tensor = cls._processar_tensor_com_padding(model, tensor_img, scale)
        except torch.cuda.OutOfMemoryError:
            # Fallback para CPU se estourar VRAM da GPU
            torch.cuda.empty_cache()
            cpu_model = cls.obter_modelo(scale).to('cpu')
            cpu_tensor = tensor_img.to('cpu')
            output_tensor = cls._processar_tensor_com_padding(cpu_model, cpu_tensor, scale)

        elapsed_time = time.perf_counter() - start_time

        # 4. Pós-processamento: Clamping e conversão para uint8 [0, 255]
        output_tensor = torch.clamp(output_tensor, 0.0, 1.0)
        output_np = output_tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
        output_uint8 = (output_np * 255.0).round().astype(np.uint8)

        output_pil = Image.fromarray(output_uint8)
        proc_w, proc_h = output_pil.size

        # 5. Exportação para PNG em memória
        buffer = io.BytesIO()
        output_pil.save(buffer, format='PNG', optimize=True)
        processed_bytes = buffer.getvalue()

        # 6. Codificação em Base64 para exibição direta no frontend
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
            "escala": scale,
            "tempo_execucao_segundos": round(elapsed_time, 3),
            "tamanho_original_kb": tamanho_original_kb,
            "tamanho_processado_kb": tamanho_processado_kb,
            "dispositivo": str(device),
        }
