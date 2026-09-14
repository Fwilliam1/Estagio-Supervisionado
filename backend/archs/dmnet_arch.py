import math
import numbers
from collections import OrderedDict
from typing import Optional, Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from einops import rearrange
from torch.autograd import Function


# ---------------------------------------------------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------------------------------------------------
def _no_grad_trunc_normal_(tensor, mean, std, a, b):
    def norm_cdf(x):
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    with torch.no_grad():
        low = norm_cdf((a - mean) / std)
        up = norm_cdf((b - mean) / std)
        tensor.uniform_(2 * low - 1, 2 * up - 1)
        tensor.erfinv_()
        tensor.mul_(std * math.sqrt(2.0))
        tensor.add_(mean)
        tensor.clamp_(min=a, max=b)
        return tensor


def trunc_normal_(tensor, mean=0.0, std=1.0, a=-2.0, b=2.0):
    return _no_grad_trunc_normal_(tensor, mean, std, a, b)


def to_3d(x):
    return rearrange(x, 'b c h w -> b (h w) c')


def to_4d(x, h, w):
    return rearrange(x, 'b (h w) c -> b c h w', h=h, w=w)


# ---------------------------------------------------------------------------------------------------------------------
# Layer Norm
# ---------------------------------------------------------------------------------------------------------------------
class BiasFree_LayerNorm(nn.Module):
    def __init__(self, normalized_shape):
        super(BiasFree_LayerNorm, self).__init__()
        if isinstance(normalized_shape, numbers.Integral):
            normalized_shape = (normalized_shape,)
        normalized_shape = torch.Size(normalized_shape)
        assert len(normalized_shape) == 1

        self.weight = nn.Parameter(torch.ones(normalized_shape))
        self.normalized_shape = normalized_shape

    def forward(self, x):
        sigma = x.var(-1, keepdim=True, unbiased=False)
        return x / torch.sqrt(sigma + 1e-5) * self.weight


class WithBias_LayerNorm(nn.Module):
    def __init__(self, normalized_shape):
        super(WithBias_LayerNorm, self).__init__()
        if isinstance(normalized_shape, numbers.Integral):
            normalized_shape = (normalized_shape,)
        normalized_shape = torch.Size(normalized_shape)
        assert len(normalized_shape) == 1

        self.weight = nn.Parameter(torch.ones(normalized_shape))
        self.bias = nn.Parameter(torch.zeros(normalized_shape))
        self.normalized_shape = normalized_shape

    def forward(self, x):
        mu = x.mean(-1, keepdim=True)
        sigma = x.var(-1, keepdim=True, unbiased=False)
        return (x - mu) / torch.sqrt(sigma + 1e-5) * self.weight + self.bias


class LayerNorm(nn.Module):
    def __init__(self, dim, LayerNorm_type):
        super(LayerNorm, self).__init__()
        if LayerNorm_type == 'BiasFree':
            self.body = BiasFree_LayerNorm(dim)
        else:
            self.body = WithBias_LayerNorm(dim)

    def forward(self, x):
        h, w = x.shape[-2:]
        return to_4d(self.body(to_3d(x)), h, w)


# ---------------------------------------------------------------------------------------------------------------------
# Patch Embedding
# ---------------------------------------------------------------------------------------------------------------------
class OverlapPatchEmbed(nn.Module):
    def __init__(self, in_c=3, embed_dim=48, bias=False):
        super(OverlapPatchEmbed, self).__init__()
        self.proj = nn.Conv2d(in_c, embed_dim, kernel_size=3, stride=1, padding=1, bias=bias)

    def forward(self, x):
        return self.proj(x)


# ---------------------------------------------------------------------------------------------------------------------
# FeedForward Networks
# ---------------------------------------------------------------------------------------------------------------------
class FeedForward(nn.Module):
    def __init__(self, dim, ffn_expansion_factor, bias, input_resolution=None):
        super(FeedForward, self).__init__()
        self.input_resolution = input_resolution
        self.dim = dim
        self.ffn_expansion_factor = ffn_expansion_factor

        hidden_features = int(dim * ffn_expansion_factor)
        self.project_in = nn.Conv2d(dim, hidden_features * 2, kernel_size=1, bias=bias)
        self.dwconv = nn.Conv2d(
            hidden_features * 2,
            hidden_features * 2,
            kernel_size=3,
            stride=1,
            padding=1,
            groups=hidden_features * 2,
            bias=bias
        )
        self.project_out = nn.Conv2d(hidden_features, dim, kernel_size=1, bias=bias)

    def forward(self, x):
        x = self.project_in(x)
        x1, x2 = self.dwconv(x).chunk(2, dim=1)
        x = F.gelu(x1) * x2
        x = self.project_out(x)
        return x


class BaseFeedForward(nn.Module):
    def __init__(self, dim, ffn_expansion_factor=2, bias=False):
        super(BaseFeedForward, self).__init__()
        hidden_features = int(dim * ffn_expansion_factor)
        self.body = nn.Sequential(
            nn.Conv2d(dim, hidden_features, 1, bias=bias),
            nn.GELU(),
            nn.Conv2d(hidden_features, dim, 1, bias=bias),
        )

    def forward(self, x):
        return self.body(x)


# ---------------------------------------------------------------------------------------------------------------------
# Sparse MDTA Attention (SMA)
# ---------------------------------------------------------------------------------------------------------------------
class SMA(nn.Module):
    def __init__(self, dim, num_heads, bias, tlc_flag=True, tlc_kernel=48, activation='relu', input_resolution=None):
        super(SMA, self).__init__()
        self.tlc_flag = tlc_flag
        self.dim = dim
        self.input_resolution = input_resolution
        self.num_heads = num_heads
        self.temperature = nn.Parameter(torch.ones(num_heads, 1, 1))

        self.qkv = nn.Conv2d(dim, dim * 3, kernel_size=1, bias=bias)
        self.qkv_dwconv = nn.Conv2d(dim * 3, dim * 3, kernel_size=3, stride=1, padding=1, groups=dim * 3, bias=bias)
        self.project_out = nn.Conv2d(dim, dim, kernel_size=1, bias=bias)

        if activation == 'relu':
            self.act = nn.ReLU()
        elif activation == 'gelu':
            self.act = nn.GELU()
        elif activation == 'sigmoid':
            self.act = nn.Sigmoid()
        else:
            self.act = nn.Identity()

        self.kernel_size = [tlc_kernel, tlc_kernel]

    def _forward(self, qkv):
        q, k, v = qkv.chunk(3, dim=1)

        q = rearrange(q, 'b (head c) h w -> b head c (h w)', head=self.num_heads)
        k = rearrange(k, 'b (head c) h w -> b head c (h w)', head=self.num_heads)
        v = rearrange(v, 'b (head c) h w -> b head c (h w)', head=self.num_heads)

        q = torch.nn.functional.normalize(q, dim=-1)
        k = torch.nn.functional.normalize(k, dim=-1)

        attn = (q @ k.transpose(-2, -1)) * self.temperature
        attn = self.act(attn)

        out = (attn @ v)
        return out

    def forward(self, x):
        b, c, h, w = x.shape
        qkv = self.qkv_dwconv(self.qkv(x))

        if self.training or not self.tlc_flag:
            out = self._forward(qkv)
            out = rearrange(out, 'b head c (h w) -> b (head c) h w', head=self.num_heads, h=h, w=w)
            out = self.project_out(out)
            return out

        qkv = self.grids(qkv)
        out = self._forward(qkv)
        out = rearrange(out, 'b head c (h w) -> b (head c) h w', head=self.num_heads, h=qkv.shape[-2], w=qkv.shape[-1])
        out = self.grids_inverse(out)

        out = self.project_out(out)
        return out

    def grids(self, x):
        b, c, h, w = x.shape
        self.original_size = (b, c // 3, h, w)
        assert b == 1
        k1, k2 = self.kernel_size
        k1 = min(h, k1)
        k2 = min(w, k2)
        num_row = (h - 1) // k1 + 1
        num_col = (w - 1) // k2 + 1
        self.nr = num_row
        self.nc = num_col

        step_j = k2 if num_col == 1 else math.ceil((w - k2) / (num_col - 1) - 1e-8)
        step_i = k1 if num_row == 1 else math.ceil((h - k1) / (num_row - 1) - 1e-8)

        parts = []
        idxes = []
        i = 0
        last_i = False
        while i < h and not last_i:
            j = 0
            if i + k1 >= h:
                i = h - k1
                last_i = True
            last_j = False
            while j < w and not last_j:
                if j + k2 >= w:
                    j = w - k2
                    last_j = True
                parts.append(x[:, :, i:i + k1, j:j + k2])
                idxes.append({'i': i, 'j': j})
                j = j + step_j
            i = i + step_i

        parts = torch.cat(parts, dim=0)
        self.idxes = idxes
        return parts

    def grids_inverse(self, outs):
        preds = torch.zeros(self.original_size, device=outs.device, dtype=outs.dtype)
        b, c, h, w = self.original_size
        count_mt = torch.zeros((b, 1, h, w), device=outs.device, dtype=outs.dtype)
        k1, k2 = self.kernel_size
        k1 = min(h, k1)
        k2 = min(w, k2)

        for cnt, each_idx in enumerate(self.idxes):
            i = each_idx['i']
            j = each_idx['j']
            preds[0, :, i:i + k1, j:j + k2] += outs[cnt, :, :, :]
            count_mt[0, 0, i:i + k1, j:j + k2] += 1.0

        del outs
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return preds / count_mt


class AttentionLayerBlock(nn.Module):
    def __init__(
        self,
        dim,
        restormer_num_heads=6,
        restormer_ffn_type='GDFN',
        restormer_ffn_expansion_factor=2.0,
        tlc_flag=True,
        tlc_kernel=48,
        activation='relu',
        input_resolution=None
    ):
        super(AttentionLayerBlock, self).__init__()
        self.dim = dim
        self.input_resolution = input_resolution
        self.norm3 = LayerNorm(dim, LayerNorm_type='WithBias')
        self.restormer_attn = SMA(
            dim,
            num_heads=restormer_num_heads,
            bias=False,
            tlc_flag=tlc_flag,
            tlc_kernel=tlc_kernel,
            activation=activation,
            input_resolution=input_resolution
        )
        self.norm4 = LayerNorm(dim, LayerNorm_type='WithBias')

        if restormer_ffn_type == 'GDFN':
            self.restormer_ffn = FeedForward(
                dim,
                ffn_expansion_factor=restormer_ffn_expansion_factor,
                bias=False,
                input_resolution=input_resolution
            )
        elif restormer_ffn_type == 'BaseFFN':
            self.restormer_ffn = BaseFeedForward(
                dim,
                ffn_expansion_factor=restormer_ffn_expansion_factor,
                bias=True
            )
        else:
            raise NotImplementedError(f'Not supported FeedForward Net type {restormer_ffn_type}')

    def forward(self, x):
        x = self.restormer_attn(self.norm3(x)) + x
        x = self.restormer_ffn(self.norm4(x)) + x
        return x


# ---------------------------------------------------------------------------------------------------------------------
# Discrete Wavelet Transform (DWT & IDWT)
# ---------------------------------------------------------------------------------------------------------------------
class DWT_Function(Function):
    @staticmethod
    def forward(ctx, x, w_ll, w_lh, w_hl, w_hh):
        x = x.contiguous()
        ctx.save_for_backward(w_ll, w_lh, w_hl, w_hh)
        ctx.shape = x.shape

        dim = x.shape[1]
        x_ll = torch.nn.functional.conv2d(x, w_ll.expand(dim, -1, -1, -1), stride=2, groups=dim)
        x_lh = torch.nn.functional.conv2d(x, w_lh.expand(dim, -1, -1, -1), stride=2, groups=dim)
        x_hl = torch.nn.functional.conv2d(x, w_hl.expand(dim, -1, -1, -1), stride=2, groups=dim)
        x_hh = torch.nn.functional.conv2d(x, w_hh.expand(dim, -1, -1, -1), stride=2, groups=dim)
        x = torch.cat([x_ll, x_lh, x_hl, x_hh], dim=1)
        return x

    @staticmethod
    def backward(ctx, dx):
        if ctx.needs_input_grad[0]:
            w_ll, w_lh, w_hl, w_hh = ctx.saved_tensors
            B, C, H, W = ctx.shape
            dx = dx.view(B, 4, -1, H // 2, W // 2)
            dx = dx.transpose(1, 2).reshape(B, -1, H // 2, W // 2)
            filters = torch.cat([w_ll, w_lh, w_hl, w_hh], dim=0).repeat(C, 1, 1, 1)
            dx = torch.nn.functional.conv_transpose2d(dx, filters, stride=2, groups=C)
        return dx, None, None, None, None


class IDWT_Function(Function):
    @staticmethod
    def forward(ctx, x, filters):
        ctx.save_for_backward(filters)
        ctx.shape = x.shape

        B, _, H, W = x.shape
        x = x.view(B, 4, -1, H, W).transpose(1, 2)
        C = x.shape[1]
        x = x.reshape(B, -1, H, W)
        filters = filters.repeat(C, 1, 1, 1)
        x = torch.nn.functional.conv_transpose2d(x, filters, stride=2, groups=C)
        return x

    @staticmethod
    def backward(ctx, dx):
        if ctx.needs_input_grad[0]:
            filters = ctx.saved_tensors
            filters = filters[0]
            B, C, H, W = ctx.shape
            C = C // 4
            dx = dx.contiguous()

            w_ll, w_lh, w_hl, w_hh = torch.unbind(filters, dim=0)
            x_ll = torch.nn.functional.conv2d(dx, w_ll.unsqueeze(1).expand(C, -1, -1, -1), stride=2, groups=C)
            x_lh = torch.nn.functional.conv2d(dx, w_lh.unsqueeze(1).expand(C, -1, -1, -1), stride=2, groups=C)
            x_hl = torch.nn.functional.conv2d(dx, w_hl.unsqueeze(1).expand(C, -1, -1, -1), stride=2, groups=C)
            x_hh = torch.nn.functional.conv2d(dx, w_hh.unsqueeze(1).expand(C, -1, -1, -1), stride=2, groups=C)
            dx = torch.cat([x_ll, x_lh, x_hl, x_hh], dim=1)
        return dx, None


class IDWT_2D(nn.Module):
    def __init__(self, wave='haar'):
        super(IDWT_2D, self).__init__()
        try:
            import pywt
            w = pywt.Wavelet(wave)
            rec_hi = torch.Tensor(w.rec_hi)
            rec_lo = torch.Tensor(w.rec_lo)
        except Exception:
            rec_lo = torch.tensor([1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0)], dtype=torch.float32)
            rec_hi = torch.tensor([1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0)], dtype=torch.float32)

        w_ll = rec_lo.unsqueeze(0) * rec_lo.unsqueeze(1)
        w_lh = rec_lo.unsqueeze(0) * rec_hi.unsqueeze(1)
        w_hl = rec_hi.unsqueeze(0) * rec_lo.unsqueeze(1)
        w_hh = rec_hi.unsqueeze(0) * rec_hi.unsqueeze(1)

        w_ll = w_ll.unsqueeze(0).unsqueeze(1)
        w_lh = w_lh.unsqueeze(0).unsqueeze(1)
        w_hl = w_hl.unsqueeze(0).unsqueeze(1)
        w_hh = w_hh.unsqueeze(0).unsqueeze(1)
        filters = torch.cat([w_ll, w_lh, w_hl, w_hh], dim=0)
        self.register_buffer('filters', filters.to(dtype=torch.float32))

    def forward(self, x):
        return IDWT_Function.apply(x, self.filters)


class DWT_2D(nn.Module):
    def __init__(self, wave='haar'):
        super(DWT_2D, self).__init__()
        try:
            import pywt
            w = pywt.Wavelet(wave)
            dec_hi = torch.Tensor(w.dec_hi[::-1])
            dec_lo = torch.Tensor(w.dec_lo[::-1])
        except Exception:
            dec_hi = torch.tensor([1.0 / math.sqrt(2.0), -1.0 / math.sqrt(2.0)], dtype=torch.float32)
            dec_lo = torch.tensor([1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0)], dtype=torch.float32)

        w_ll = dec_lo.unsqueeze(0) * dec_lo.unsqueeze(1)
        w_lh = dec_lo.unsqueeze(0) * dec_hi.unsqueeze(1)
        w_hl = dec_hi.unsqueeze(0) * dec_lo.unsqueeze(1)
        w_hh = dec_hi.unsqueeze(0) * dec_hi.unsqueeze(1)

        self.register_buffer('w_ll', w_ll.unsqueeze(0).unsqueeze(0).to(dtype=torch.float32))
        self.register_buffer('w_lh', w_lh.unsqueeze(0).unsqueeze(0).to(dtype=torch.float32))
        self.register_buffer('w_hl', w_hl.unsqueeze(0).unsqueeze(0).to(dtype=torch.float32))
        self.register_buffer('w_hh', w_hh.unsqueeze(0).unsqueeze(0).to(dtype=torch.float32))

    def forward(self, x):
        return DWT_Function.apply(x, self.w_ll, self.w_lh, self.w_hl, self.w_hh)


# ---------------------------------------------------------------------------------------------------------------------
# Pure PyTorch Dynamic Depthwise Convolution (IDynamic)
# Runs universally on CPU and GPU without CuPy or C++ CUDA extensions.
# ---------------------------------------------------------------------------------------------------------------------
class IDynamic(nn.Module):
    """
    IDynamic Dynamic Depthwise Convolution.
    Mathematically identical to the CUDA kernel in DemystifyLocalViT / DMNet,
    implemented in vectorized PyTorch for 100% portability across CPU/GPU without CuPy.
    """
    def __init__(self, channels, kernel_size=7, group_channels=8, bias=True):
        super(IDynamic, self).__init__()
        self.kernel_size = kernel_size
        self.channels = channels
        reduction_ratio = 8
        self.group_channels = group_channels
        self.groups = self.channels // self.group_channels
        self.conv1 = nn.Sequential(
            nn.Conv2d(channels, channels // reduction_ratio, 1, bias=bias),
            nn.Conv2d(
                channels // reduction_ratio,
                channels // reduction_ratio,
                kernel_size=kernel_size,
                padding=kernel_size // 2,
                groups=channels // reduction_ratio,
                bias=bias
            ),
        )
        self.conv2 = nn.Sequential(
            nn.Conv2d(channels // reduction_ratio, kernel_size ** 2 * self.groups, 1, bias=bias)
        )

    def forward(self, x_main, x):
        weight = self.conv2(self.conv1(x))
        b, _, h, w = weight.shape
        weight = weight.view(b, self.groups, self.kernel_size, self.kernel_size, h, w)

        pad = (self.kernel_size - 1) // 2
        x_unfold = F.unfold(x_main, kernel_size=(self.kernel_size, self.kernel_size), padding=(pad, pad), stride=1)
        x_unfold = x_unfold.view(b, self.groups, x_main.shape[1] // self.groups, self.kernel_size * self.kernel_size, h, w)
        w_flat = weight.view(b, self.groups, 1, self.kernel_size * self.kernel_size, h, w)
        out = (x_unfold * w_flat).sum(dim=3).view(b, x_main.shape[1], h, w)
        return out


# ---------------------------------------------------------------------------------------------------------------------
# Wavelet Multi-head Attention (WMA)
# ---------------------------------------------------------------------------------------------------------------------
class WMA(nn.Module):
    def __init__(self, dim, num_heads, bias=False, tlc_flag=True, tlc_kernel=48, activation='relu', input_resolution=None):
        super(WMA, self).__init__()
        self.tlc_flag = tlc_flag
        self.dim = dim
        self.input_resolution = input_resolution
        self.num_heads = num_heads
        self.temperature = nn.Parameter(torch.ones(num_heads, 1, 1))

        self.dwt = DWT_2D(wave='haar')
        self.reduce = nn.Sequential(
            nn.Conv2d(dim, dim // 4, kernel_size=1, padding=0, stride=1),
            nn.ReLU(inplace=True),
        )

        self.filter = IDynamic(channels=dim, kernel_size=7, group_channels=num_heads)

        self.qkv = nn.Conv2d(dim, dim * 3, kernel_size=1, bias=bias)
        self.qkv_dwconv = nn.Conv2d(dim * 3, dim * 3, kernel_size=3, stride=1, padding=1, groups=dim * 3, bias=bias)
        self.project_out = nn.Conv2d(dim // 4, dim, kernel_size=1, bias=bias)
        self.idwt_sa = IDWT_2D(wave='haar')

        if activation == 'relu':
            self.act = nn.ReLU()
        elif activation == 'gelu':
            self.act = nn.GELU()
        elif activation == 'sigmoid':
            self.act = nn.Sigmoid()
        else:
            self.act = nn.Identity()

        self.kernel_size = [tlc_kernel, tlc_kernel]

    def _forward(self, x):
        x_dwt = self.dwt(self.reduce(x))

        qkv = self.qkv_dwconv(self.qkv(x_dwt))
        q, k, v = qkv.chunk(3, dim=1)

        q = rearrange(q, 'b (head c) h w -> b head c (h w)', head=self.num_heads)
        k = rearrange(k, 'b (head c) h w -> b head c (h w)', head=self.num_heads)
        v = rearrange(v, 'b (head c) h w -> b head c (h w)', head=self.num_heads)

        q = torch.nn.functional.normalize(q, dim=-1)
        k = torch.nn.functional.normalize(k, dim=-1)

        attn = (q @ k.transpose(-2, -1)) * self.temperature
        attn = self.act(attn)

        out = (attn @ v)
        return out, x_dwt

    def forward(self, x):
        b, c, h, w = x.shape
        qkv = x

        if self.training or not self.tlc_flag:
            out, x_dwt = self._forward(qkv)
            out = rearrange(out, 'b head c (h w) -> b (head c) h w', head=self.num_heads, h=h // 2, w=w // 2)
            out = self.filter(out, x_dwt)
            out = self.idwt_sa(out)
            out = self.project_out(out)
            return out

        qkv = self.grids(qkv)
        out, x_dwt = self._forward(qkv)
        out = rearrange(out, 'b head c (h w) -> b (head c) h w', head=self.num_heads, h=qkv.shape[-2] // 2, w=qkv.shape[-1] // 2)
        out = self.filter(out, x_dwt)
        out = self.idwt_sa(out)
        out = self.project_out(out)

        out = self.grids_inverse(out)
        return out

    def grids(self, x):
        b, c, h, w = x.shape
        self.original_size = (b, c, h, w)
        assert b == 1
        k1, k2 = self.kernel_size
        k1 = min(h, k1)
        k2 = min(w, k2)
        num_row = (h - 1) // k1 + 1
        num_col = (w - 1) // k2 + 1
        self.nr = num_row
        self.nc = num_col

        step_j = k2 if num_col == 1 else math.ceil((w - k2) / (num_col - 1) - 1e-8)
        step_i = k1 if num_row == 1 else math.ceil((h - k1) / (num_row - 1) - 1e-8)

        parts = []
        idxes = []
        i = 0
        last_i = False
        while i < h and not last_i:
            j = 0
            if i + k1 >= h:
                i = h - k1
                last_i = True
            last_j = False
            while j < w and not last_j:
                if j + k2 >= w:
                    j = w - k2
                    last_j = True
                parts.append(x[:, :, i:i + k1, j:j + k2])
                idxes.append({'i': i, 'j': j})
                j = j + step_j
            i = i + step_i

        parts = torch.cat(parts, dim=0)
        self.idxes = idxes
        return parts

    def grids_inverse(self, outs):
        preds = torch.zeros(self.original_size, device=outs.device, dtype=outs.dtype)
        b, c, h, w = self.original_size
        count_mt = torch.zeros((b, 1, h, w), device=outs.device, dtype=outs.dtype)
        k1, k2 = self.kernel_size
        k1 = min(h, k1)
        k2 = min(w, k2)

        for cnt, each_idx in enumerate(self.idxes):
            i = each_idx['i']
            j = each_idx['j']
            preds[0, :, i:i + k1, j:j + k2] += outs[cnt, :, :, :]
            count_mt[0, 0, i:i + k1, j:j + k2] += 1.0

        del outs
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return preds / count_mt


class WaveAttentionLayerBlock(nn.Module):
    def __init__(
        self,
        dim,
        restormer_num_heads=6,
        restormer_ffn_type='GDFN',
        restormer_ffn_expansion_factor=2.0,
        tlc_flag=True,
        tlc_kernel=48,
        activation='relu',
        input_resolution=None
    ):
        super(WaveAttentionLayerBlock, self).__init__()
        self.dim = dim
        self.input_resolution = input_resolution
        self.norm3 = LayerNorm(dim, LayerNorm_type='WithBias')
        self.restormer_attn = WMA(
            dim=dim,
            num_heads=restormer_num_heads,
            bias=False,
            tlc_flag=tlc_flag,
            tlc_kernel=tlc_kernel,
            activation=activation,
            input_resolution=input_resolution
        )
        self.norm4 = LayerNorm(dim, LayerNorm_type='WithBias')

        if restormer_ffn_type == 'GDFN':
            self.restormer_ffn = FeedForward(
                dim,
                ffn_expansion_factor=restormer_ffn_expansion_factor,
                bias=False,
                input_resolution=input_resolution
            )
        elif restormer_ffn_type == 'BaseFFN':
            self.restormer_ffn = BaseFeedForward(
                dim,
                ffn_expansion_factor=restormer_ffn_expansion_factor,
                bias=True
            )
        else:
            raise NotImplementedError(f'Not supported FeedForward Net type {restormer_ffn_type}')

    def forward(self, x):
        x = self.restormer_attn(self.norm3(x)) + x
        x = self.restormer_ffn(self.norm4(x)) + x
        return x


# ---------------------------------------------------------------------------------------------------------------------
# BuildBlock
# ---------------------------------------------------------------------------------------------------------------------
class BuildBlock(nn.Module):
    def __init__(
        self,
        dim,
        blocks=3,
        buildblock_type='Wave',
        window_size=7,
        restormer_num_heads=6,
        restormer_ffn_type='GDFN',
        restormer_ffn_expansion_factor=2.0,
        tlc_flag=True,
        tlc_kernel=48,
        activation='relu',
        input_resolution=None
    ):
        super(BuildBlock, self).__init__()
        self.input_resolution = input_resolution
        self.dim = dim
        self.blocks = blocks
        self.buildblock_type = buildblock_type
        self.window_size = window_size
        self.tlc = tlc_flag

        body = []
        if buildblock_type == 'Wave':
            for _ in range(blocks):
                body.append(AttentionLayerBlock(
                    dim,
                    restormer_num_heads,
                    restormer_ffn_type,
                    restormer_ffn_expansion_factor,
                    tlc_flag,
                    tlc_kernel,
                    activation,
                    input_resolution=input_resolution
                ))
                body.append(WaveAttentionLayerBlock(
                    dim,
                    restormer_num_heads,
                    restormer_ffn_type,
                    restormer_ffn_expansion_factor,
                    tlc_flag,
                    tlc_kernel,
                    activation,
                    input_resolution=input_resolution
                ))

        body.append(nn.Conv2d(dim, dim, 3, 1, 1))
        self.body = nn.Sequential(*body)

    def forward(self, x):
        return self.body(x) + x


# ---------------------------------------------------------------------------------------------------------------------
# Upsampling
# ---------------------------------------------------------------------------------------------------------------------
class UpsampleOneStep(nn.Sequential):
    def __init__(self, scale, num_feat, num_out_ch, input_resolution=None):
        self.num_feat = num_feat
        self.input_resolution = input_resolution
        m = [
            nn.Conv2d(num_feat, (scale ** 2) * num_out_ch, 3, 1, 1),
            nn.PixelShuffle(scale)
        ]
        super(UpsampleOneStep, self).__init__(*m)


class Upsample(nn.Sequential):
    def __init__(self, scale, num_feat):
        m = []
        if (scale & (scale - 1)) == 0:
            for _ in range(int(math.log(scale, 2))):
                m.append(nn.Conv2d(num_feat, 4 * num_feat, 3, 1, 1))
                m.append(nn.PixelShuffle(2))
        elif scale == 3:
            m.append(nn.Conv2d(num_feat, 9 * num_feat, 3, 1, 1))
            m.append(nn.PixelShuffle(3))
        else:
            raise ValueError(f'scale {scale} is not supported. Supported scales: 2^n and 3.')
        super(Upsample, self).__init__(*m)


# ---------------------------------------------------------------------------------------------------------------------
# Main DMNet Network Architecture
# ---------------------------------------------------------------------------------------------------------------------
class DMNet(nn.Module):
    """
    DMNet (Dual Multi-scale Attention Network for Image Super-Resolution).
    100% self-contained PyTorch implementation for inference on CPU or GPU.
    """
    def __init__(
        self,
        in_chans=3,
        dim=48,
        groups=3,
        blocks=3,
        buildblock_type='Wave',
        window_size=7,
        restormer_num_heads=8,
        restormer_ffn_type='GDFN',
        restormer_ffn_expansion_factor=2.0,
        tlc_flag=True,
        tlc_kernel=64,
        activation='relu',
        upscale=4,
        img_range=1.0,
        upsampler='pixelshuffledirect',
        body_norm=False,
        input_resolution=None,
        **kwargs
    ):
        super(DMNet, self).__init__()
        self.dim = dim
        self.input_resolution = input_resolution
        self.img_range = img_range

        if in_chans == 3:
            rgb_mean = (0.4488, 0.4371, 0.4040)
            self.register_buffer('mean', torch.Tensor(rgb_mean).view(1, 3, 1, 1), persistent=False)
        else:
            self.register_buffer('mean', torch.zeros(1, 1, 1, 1), persistent=False)

        self.upscale = upscale
        self.upsampler = upsampler

        # 1. Shallow feature extraction
        self.overlap_embed = nn.Sequential(OverlapPatchEmbed(in_chans, dim, bias=False))

        # 2. Deep feature extraction
        m_body = []
        if body_norm:
            m_body.append(LayerNorm(dim, LayerNorm_type='WithBias'))

        for _ in range(groups):
            m_body.append(BuildBlock(
                dim,
                blocks,
                buildblock_type,
                window_size,
                restormer_num_heads,
                restormer_ffn_type,
                restormer_ffn_expansion_factor,
                tlc_flag,
                tlc_kernel,
                activation,
                input_resolution=input_resolution
            ))

        if body_norm:
            m_body.append(LayerNorm(dim, LayerNorm_type='WithBias'))

        m_body.append(nn.Conv2d(dim, dim, kernel_size=(3, 3), padding=(1, 1)))
        self.deep_feature_extraction = nn.Sequential(*m_body)

        # 3. High quality image reconstruction
        num_feat = 64
        embed_dim = dim
        num_out_ch = in_chans

        if self.upsampler == 'pixelshuffledirect':
            self.upsample = UpsampleOneStep(upscale, embed_dim, num_out_ch, input_resolution=self.input_resolution)
        elif self.upsampler == 'pixelshuffle':
            self.conv_before_upsample = nn.Sequential(
                nn.Conv2d(embed_dim, num_feat, 3, 1, 1),
                nn.LeakyReLU(inplace=True)
            )
            self.upsample = Upsample(upscale, num_feat)
            self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        else:
            self.conv_last = nn.Conv2d(embed_dim, num_out_ch, 3, 1, 1)

        self.apply(self._init_weights)

    def _init_weights(self, m):
        if isinstance(m, nn.Linear):
            trunc_normal_(m.weight, std=0.02)
            if m.bias is not None:
                nn.init.constant_(m.bias, 0)
        elif isinstance(m, nn.LayerNorm):
            nn.init.constant_(m.bias, 0)
            nn.init.constant_(m.weight, 1.0)

    @torch.jit.ignore
    def no_weight_decay(self):
        return {'absolute_pos_embed'}

    @torch.jit.ignore
    def no_weight_decay_keywords(self):
        return {'relative_position_bias_table'}

    def forward(self, x):
        mean = self.mean.to(device=x.device, dtype=x.dtype)
        x = (x - mean) * self.img_range

        if self.upsampler == 'pixelshuffledirect':
            x = self.overlap_embed(x)
            x = self.deep_feature_extraction(x) + x
            x = self.upsample(x)
        elif self.upsampler == 'pixelshuffle':
            x = self.overlap_embed(x)
            x = self.deep_feature_extraction(x) + x
            x = self.conv_before_upsample(x)
            x = self.conv_last(self.upsample(x))
        else:
            x = self.overlap_embed(x)
            x = self.deep_feature_extraction(x) + x
            x = self.conv_last(x)

        x = x / self.img_range + mean
        return x
