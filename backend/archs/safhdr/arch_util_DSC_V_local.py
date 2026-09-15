import torch
import torch.nn as nn
import torch.nn.init as init
import torch.nn.functional as F


def initialize_weights(net_l, scale=1):
    if not isinstance(net_l, list):
        net_l = [net_l]
    for net in net_l:
        for m in net.modules():
            if isinstance(m, nn.Conv2d):
                init.kaiming_normal_(m.weight, a=0, mode='fan_in')
                m.weight.data *= scale  # for residual block
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.Linear):
                init.kaiming_normal_(m.weight, a=0, mode='fan_in')
                m.weight.data *= scale
                if m.bias is not None:
                    m.bias.data.zero_()
            elif isinstance(m, nn.BatchNorm2d):
                init.constant_(m.weight, 1)
                init.constant_(m.bias.data, 0.0)


def make_layer(block, n_layers):
    layers = []
    for _ in range(n_layers):
        layers.append(block())
    return nn.Sequential(*layers)


class DSC(nn.Module):
    """Implementação genérica de Depthwise Separable Convolution"""
    def __init__(self, in_nc, out_nc, kernel_size, stride=1, padding=1, bias=True):
        super(DSC, self).__init__()
        self.depthwise = nn.Conv2d(in_nc, in_nc, kernel_size=kernel_size, 
                                   stride=stride, padding=padding, groups=in_nc, bias=bias)
        self.pointwise = nn.Conv2d(in_nc, out_nc, kernel_size=1, bias=bias)

    def forward(self, x):
        out = self.depthwise(x)
        out = self.pointwise(out)
        return out

class SFTLayer(nn.Module):
    def __init__(self, in_nc=24, out_nc=48, nf=24):
        super(SFTLayer, self).__init__()
        # Mantemos Conv 1x1 originais pois DSC 1x1 é redundante
        self.SFT_scale_conv0 = nn.Conv2d(in_nc, nf, 1)
        self.SFT_scale_conv1 = nn.Conv2d(nf, out_nc, 1)
        self.SFT_shift_conv0 = nn.Conv2d(in_nc, nf, 1)
        self.SFT_shift_conv1 = nn.Conv2d(nf, out_nc, 1)

    def forward(self, x):
        # x[0]: fea (feature map); x[1]: cond (condition)
        scale = self.SFT_scale_conv1(F.leaky_relu(self.SFT_scale_conv0(x[1]), 0.1, inplace=True))
        shift = self.SFT_shift_conv1(F.leaky_relu(self.SFT_shift_conv0(x[1]), 0.1, inplace=True))
        return x[0] * (scale + 1) + shift

class ResBlock_with_SFT(nn.Module):
    def __init__(self, nf=48, cond_nc=24):
        super(ResBlock_with_SFT, self).__init__()
        
        # SFT 1
        self.sft1 = SFTLayer(in_nc=cond_nc, out_nc=nf, nf=cond_nc)
        # Substituindo nn.Conv2d 3x3 por DSC
        self.conv1 = DSC(nf, nf, kernel_size=3, stride=1, padding=1)
        
        # SFT 2
        self.sft2 = SFTLayer(in_nc=cond_nc, out_nc=nf, nf=cond_nc)
        # Substituindo nn.Conv2d 3x3 por DSC
        self.conv2 = DSC(nf, nf, kernel_size=3, stride=1, padding=1)

        # Inicialização (ajuste conforme sua função de inicialização)
        # self.initialize_weights([self.conv1, self.conv2], 0.1)

    def forward(self, x):
        # x[0]: fea (NF canais); x[1]: cond (In_NC canais)
        fea = self.sft1(x)
        fea = F.relu(self.conv1(fea), inplace=True)
        fea = self.sft2((fea, x[1]))
        fea = self.conv2(fea)
        
        # Conexão residual
        return (x[0] + fea, x[1])


class ResidualBlock_noBN(nn.Module):
    '''Residual block w/o BN
    ---Conv-ReLU-Conv-+-
     |________________|
    '''

    def __init__(self, nf=64):
        super(ResidualBlock_noBN, self).__init__()
        self.conv1 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        self.conv2 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)

        # initialization
        initialize_weights([self.conv1, self.conv2], 0.1)

    def forward(self, x):
        identity = x
        out = F.relu(self.conv1(x), inplace=True)
        out = self.conv2(out)
        return identity + out


def flow_warp(x, flow, interp_mode='bilinear', padding_mode='zeros'):
    """Warp an image or feature map with optical flow
    Args:
        x (Tensor): size (N, C, H, W)
        flow (Tensor): size (N, H, W, 2), normal value
        interp_mode (str): 'nearest' or 'bilinear'
        padding_mode (str): 'zeros' or 'border' or 'reflection'

    Returns:
        Tensor: warped image or feature map
    """
    assert x.size()[-2:] == flow.size()[1:3]
    B, C, H, W = x.size()
    # mesh grid
    grid_y, grid_x = torch.meshgrid(torch.arange(0, H), torch.arange(0, W))
    grid = torch.stack((grid_x, grid_y), 2).float()  # W(x), H(y), 2
    grid.requires_grad = False
    grid = grid.type_as(x)
    vgrid = grid + flow
    # scale grid to [-1,1]
    vgrid_x = 2.0 * vgrid[:, :, :, 0] / max(W - 1, 1) - 1.0
    vgrid_y = 2.0 * vgrid[:, :, :, 1] / max(H - 1, 1) - 1.0
    vgrid_scaled = torch.stack((vgrid_x, vgrid_y), dim=3)
    output = F.grid_sample(x, vgrid_scaled, mode=interp_mode, padding_mode=padding_mode)
    return output
