import functools
import torch 
import torch.nn as nn
import torch.nn.functional as F

try:
    import archs.safhdr.arch_util_local as arch_util_local
    import archs.safhdr.arch_util_DSC_V_local as arch_util_hdrunet 
    
except ImportError:
    from . import arch_util_local as arch_util_local
    from . import arch_util_DSC_V_local as arch_util_hdrunet

class BlockConv(nn.Module):
    def __init__(self, in_nc=64, out_nc=64, nf=64):
        super(BlockConv, self).__init__()

        self.camada1 = nn.Sequential(
            nn.Conv2d(in_nc, nf, kernel_size=3, stride=1, padding=1),
            nn.PReLU(nf),
            nn.Conv2d(nf, nf, kernel_size=1),
            nn.PReLU(nf),
            nn.Conv2d(nf, nf, kernel_size=1),
            nn.PReLU(nf),

        )
        self.camada1_cond = nn.Conv2d(nf, 24, 1)

        self.camada2 = nn.Conv2d(in_nc, nf, kernel_size=3, stride=1, padding=1)

        basic_block = functools.partial(arch_util_hdrunet.ResBlock_with_SFT, nf=nf)
        self.recon_trunk1 = arch_util_hdrunet.make_layer(basic_block, 4)

        self.camada2_rb = nn.Sequential(
            nn.Conv2d(in_nc, nf, kernel_size=3, stride=1, padding=1),
            nn.PReLU(nf),
            nn.Conv2d(nf, nf, kernel_size=1),
            nn.PReLU(nf),
        )

        self.camada2_last_conv = nn.Conv2d(nf, nf, kernel_size=1)
        self.conv_last = nn.Conv2d(nf, out_nc, kernel_size=3, stride=1, padding=1)

    def forward(self, x):
        mask = self.camada1(x)
        cond = self.camada1_cond(mask)
        
        fea = self.camada2(x)
        fea, _ = self.recon_trunk1((fea, cond))

        rb = self.camada2_rb(x)
        fea = fea + rb
        fea = self.camada2_last_conv(fea)

        out = fea + mask
        out = self.conv_last(out)

        return out
    
class channel_atten(nn.Module):
    def __init__(self, ch_in, reduction=16):
        super(channel_atten, self).__init__()
        self.ch_in = ch_in
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Sequential(
            nn.Linear(ch_in, ch_in // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(ch_in // reduction, ch_in, bias=False),
            nn.Sigmoid()
        )

    def forward(self, x):
        b, c, _, _ = x.size()
        y = self.avg_pool(x).view(b, c)
        a = x * y.view(b, c, 1, 1).expand_as(x)

        y = self.fc(y).view(b, c, 1, 1)
        return x * y.expand_as(x)

class attention_offset(nn.Module):
    def __init__(self, in_nc=3, out_nc=3, nf=64):
        super(attention_offset, self).__init__()
        self.ca = channel_atten(ch_in=in_nc, reduction=16)
        self.conv1 = nn.Conv2d(in_nc, nf, 1)
        self.conv2 = nn.Conv2d(nf, out_nc, 3, 1, 1)

        # self.mask = soft_mask()
        
    def forward(self, x):
        # x = self.mask(x)
        x1 = self.ca(x)
        x2 = self.conv1(x)
        x2 = self.conv2(x2)
        return x1 * x2

class HDRUNet(nn.Module):

    def __init__(self, in_nc=3, out_nc=3, nf=64, act_type='relu'):
        super(HDRUNet, self).__init__()
        
        self.conv_first = nn.Conv2d(in_nc, nf, 3, 1, 1)
        
        self.HR_conv1 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)

        self.down_conv1 = nn.Conv2d(nf, nf, 3, 2, 1)
        self.down_conv2 = nn.Conv2d(nf, nf, 3, 2, 1)
        
        basic_block = functools.partial(arch_util_local.ResBlock_with_SFT, nf=nf)
        self.recon_trunk1 = arch_util_local.make_layer(basic_block, 2)
        self.recon_trunk2 = arch_util_local.make_layer(basic_block, 2)
        
        self.up_conv1 = nn.Sequential(
                                        nn.Conv2d(nf, nf*4, 3, 1, 1),
                                        nn.PixelShuffle(2)
                                        )
        self.up_conv2 = nn.Sequential(
                                        nn.Conv2d(nf, nf*4, 3, 1, 1), 
                                        nn.PixelShuffle(2)
                                        )

        self.HR_conv2 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)


        self.conv_last = nn.Conv2d(nf, out_nc, 3, 1, 1, bias=True)

        cond_in_nc=3
        cond_nf=64
        self.BlockConv0 = BlockConv()
        self.BlockConv1 = BlockConv()
        
        # Diferença para o RFHDRNet com SFT
        self.attention_offset1 = attention_offset(in_nc=nf, out_nc=nf, nf=nf)
        self.attention_offset2 = attention_offset(in_nc=nf, out_nc=nf, nf=nf)

        self.cond2 = nn.Conv2d(nf, 32, 1)
        self.cond3 = nn.Conv2d(nf, 32, 1)
        
        self.convMask1 = nn.Conv2d(in_nc, nf, 3, 1, 1)
        
        self.mask_est = nn.Sequential(nn.Conv2d(nf, nf, 3, 1, 1), 
                                      nn.PReLU(nf), 
                                      nn.Conv2d(nf, nf, 3, 1, 1),
                                      nn.PReLU(nf), 
                                      nn.Conv2d(nf, nf, 3, 1, 1),
                                      nn.PReLU(nf),
                                      nn.Conv2d(nf, nf, 3, 1, 1), 
                                      nn.PReLU(nf),
                                     )

        # activation function
        if act_type == 'relu':
            self.act = nn.ReLU(inplace=True)
        elif act_type == 'leakyrelu':
            self.act = nn.LeakyReLU(negative_slope=0.1, inplace=True)

    def forward(self, x):
        # x[0]: img; x[1]: cond
        mask1 = self.convMask1(x)
        mask = self.mask_est(mask1)

        # cond = self.cond_first(x[1])   
        
        # cond2 = self.CondNet2(cond)
        
        # cond3 = self.CondNet3(cond)
        
        fea = self.act(self.conv_first(x))

        fea0 = self.act(self.HR_conv1(fea))

        fea1 = self.act(self.down_conv1(fea0))

        cond2 = self.attention_offset1(fea1)
        cond2 = self.cond2(cond2)
        
        fea1, _ = self.recon_trunk1((fea1, cond2))

        fea2 = self.act(self.down_conv2(fea1))

        cond3 = self.attention_offset2(fea2)
        cond3 = self.cond3(cond3)
        
        out, _ = self.recon_trunk2((fea2, cond3))
        
        out = out + fea2
        
        out = self.BlockConv0(out)
        out = self.act(self.up_conv1(out)) + fea1
        
        
        out = self.BlockConv1(out)
        out = self.act(self.up_conv2(out)) 
        out = self.act(self.HR_conv2(out)) + fea

        
        out = (mask + mask1) + out
        out = self.conv_last(out)
        
        return out
