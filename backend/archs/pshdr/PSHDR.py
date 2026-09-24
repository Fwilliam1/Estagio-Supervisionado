import functools
import torch.nn as nn

try:
    import archs.pshdr.arch_util as arch_util
    import archs.pshdr.arch_util_hdrunet as arch_util_hdrunet
except ImportError:
    from . import arch_util as arch_util
    from . import arch_util_hdrunet as arch_util_hdrunet


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
        self.camada1_cond = nn.Conv2d(nf, 32, 1)

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


class HDRUNet(nn.Module):
    def __init__(self, in_nc=3, out_nc=3, nf=64, act_type='relu'):
        super(HDRUNet, self).__init__()

        self.conv_first = nn.Conv2d(in_nc, nf, 3, 1, 1)
        self.HR_conv1 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)

        self.down_conv1 = nn.Conv2d(nf, nf, 3, 2, 1)
        self.down_conv2 = nn.Conv2d(nf, nf, 3, 2, 1)

        basic_block = functools.partial(arch_util.ResBlock_with_SFT, nf=nf)
        self.recon_trunk1 = arch_util.make_layer(basic_block, 2)
        self.recon_trunk2 = arch_util.make_layer(basic_block, 2)

        self.up_conv1 = nn.Sequential(
            nn.Conv2d(nf, nf * 4, 3, 1, 1),
            nn.PixelShuffle(2),
        )
        self.up_conv2 = nn.Sequential(
            nn.Conv2d(nf, nf * 4, 3, 1, 1),
            nn.PixelShuffle(2),
        )

        self.HR_conv2 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        self.conv_last = nn.Conv2d(nf, out_nc, 3, 1, 1, bias=True)

        cond_in_nc = 3
        cond_nf = 64
        self.BlockConv0 = BlockConv()
        self.BlockConv1 = BlockConv()

        self.cond_first = nn.Sequential(
            nn.Conv2d(cond_in_nc, cond_nf, 3, 1, 1),
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, cond_nf, 1),
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, cond_nf, 1),
            nn.LeakyReLU(0.1, True),
        )

        self.CondNet2 = nn.Sequential(
            nn.Conv2d(cond_nf, cond_nf, 3, 2, 1),
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, 32, 1),
        )

        self.CondNet3 = nn.Sequential(
            nn.Conv2d(cond_nf, cond_nf, 3, 2, 1),
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, 32, 3, 2, 1),
        )

        # activation function
        if act_type == 'relu':
            self.act = nn.ReLU(inplace=True)
        elif act_type == 'leakyrelu':
            self.act = nn.LeakyReLU(negative_slope=0.1, inplace=True)

    def forward(self, x):
        cond = self.cond_first(x)
        cond2 = self.CondNet2(cond)
        cond3 = self.CondNet3(cond)

        fea = self.act(self.conv_first(x))
        fea0 = self.act(self.HR_conv1(fea))

        fea1 = self.act(self.down_conv1(fea0))
        fea1, _ = self.recon_trunk1((fea1, cond2))

        fea2 = self.act(self.down_conv2(fea1))
        out, _ = self.recon_trunk2((fea2, cond3))

        out = out + fea2

        out = self.BlockConv0(out)
        out = self.act(self.up_conv1(out)) + fea1

        out = self.BlockConv1(out)
        out = self.act(self.up_conv2(out))
        out = self.act(self.HR_conv2(out)) + fea

        out = self.conv_last(out)

        return out
