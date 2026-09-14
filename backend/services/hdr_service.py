import io
import time
import base64
from typing import Dict, Any
import numpy as np
from PIL import Image
import cv2

from .exceptions import ValidacaoError, ServiceException


class HdrService:
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
