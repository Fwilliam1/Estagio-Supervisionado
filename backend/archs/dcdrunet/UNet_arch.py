import functools
import torch
import torch.nn as nn
import torch.nn.functional as F

try:
    from . import arch_util
except ImportError:
    try:
        import models.modules.DCDRUNET.arch_util as arch_util
    except ImportError:
        import arch_util as arch_util


class HDRUNet(nn.Module):

    def __init__(self, in_nc=3, out_nc=3, nf=64, act_type="relu"):
        super(HDRUNet, self).__init__()

        self.conv_first = nn.Conv2d(in_nc, nf, 3, 1, 1)

        self.SFT_layer1 = arch_util.SFTLayer()
        self.HR_conv1 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)

        self.down_conv1 = nn.Conv2d(nf, nf, 3, 2, 1)
        self.down_conv2 = nn.Conv2d(nf, nf, 3, 2, 1)

        basic_block = functools.partial(arch_util.ResBlock_with_SFT, nf=nf)
        self.recon_trunk1 = arch_util.make_layer(basic_block, 2)
        self.recon_trunk2 = arch_util.make_layer(basic_block, 4)
        self.recon_trunk3 = arch_util.make_layer(basic_block, 2)

        self.up_conv1 = nn.Sequential(
            nn.Conv2d(nf, nf * 4, 3, 1, 1), nn.PixelShuffle(2)
        )
        self.up_conv2 = nn.Sequential(
            nn.Conv2d(nf, nf * 4, 3, 1, 1), nn.PixelShuffle(2)
        )

        self.SFT_layer2 = arch_util.SFTLayer()
        self.HR_conv2 = nn.Conv2d(nf, nf, 3, 1, 1, bias=True)
        self.conv_last = nn.Conv2d(nf, out_nc, 3, 1, 1, bias=True)

        cond_in_nc = 3
        cond_nf = 64
        self.cond_first = nn.Sequential(
            nn.Conv2d(cond_in_nc, cond_nf, 3, 2),  # Reduccion x2
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, cond_nf, 1, 2),  # Reduccion x2
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, cond_nf, 1, 1),
            nn.LeakyReLU(0.1, True),
        )
        self.CondNet1 = nn.Sequential(
            nn.Conv2d(cond_nf, cond_nf * 4, 1, 1),
            nn.PixelShuffle(2),  # Upscale x2
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, 32 * 4, 1, 1),
            nn.PixelShuffle(2),  # Upscale x2
        )
        self.CondNet2 = nn.Sequential(
            nn.Conv2d(cond_nf, cond_nf * 4, 1, 1),
            nn.PixelShuffle(2),  # Upscale x2
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, 32, 1),
        )
        self.CondNet3 = nn.Sequential(
            nn.Conv2d(cond_nf, cond_nf, 3, 1, 1),
            nn.LeakyReLU(0.1, True),
            nn.Conv2d(cond_nf, 32, 3, 1, 1),
        )

        self.mask_est = nn.Sequential(
            nn.Conv2d(in_nc, nf, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(nf, nf, 3, 1, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(nf, nf, 1),
            nn.ReLU(inplace=True),
            nn.Conv2d(nf, out_nc, 1),
        )

        # activation function
        if act_type == "relu":
            self.act = nn.ReLU(inplace=True)
        elif act_type == "leakyrelu":
            self.act = nn.LeakyReLU(negative_slope=0.1, inplace=True)

    def forward(self, img, cond=None):
        # The repository's condition model passes a pair to the generator;
        # keep support for the original DCDRUNet(img, cond) call as well.
        if cond is None:
            if not isinstance(img, (tuple, list)) or len(img) != 2:
                raise ValueError("DCDRUNet expects (image, condition)")
            img, cond = img

        x = (img, cond)
        # x[0]: img; x[1]: cond
        mask = self.mask_est(x[0])  # Tone Net

        cond = self.cond_first(x[1])

        cond1 = self.CondNet1(cond)
        cond2 = self.CondNet2(cond)
        cond3 = self.CondNet3(cond)
        # print(f"{img.shape=} {cond1.shape=}, {cond2.shape=},{cond3.shape=}")
        fea0 = self.act(self.conv_first(x[0]))

        fea0 = self.SFT_layer1((fea0, cond1))
        fea0 = self.act(self.HR_conv1(fea0))

        fea1 = self.act(self.down_conv1(fea0))
        fea1, _ = self.recon_trunk1((fea1, cond2))

        fea2 = self.act(self.down_conv2(fea1))
        out, _ = self.recon_trunk2((fea2, cond3))
        out = out + fea2

        out = self.act(self.up_conv1(out)) + fea1
        out, _ = self.recon_trunk3((out, cond2))

        out = self.act(self.up_conv2(out)) + fea0
        out = self.SFT_layer2((out, cond1))
        out = self.act(self.HR_conv2(out))

        out = self.conv_last(out)
        out = mask * x[0] + out
        return out


if __name__ == "__main__":
    import time
    import pynvml
    from thop import profile

    model = HDRUNet().cuda().eval()

    x1 = torch.randn(1, 3, 1600, 900).cuda()
    x2 = torch.randn(1, 3, 1600, 900).cuda()
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    gpuName = pynvml.nvmlDeviceGetName(handle)
    print(gpuName)

    with torch.no_grad():
        for i in range(10):
            out = model(x1, x2)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        time_stamp = time.time()
        for i in range(10):
            out = model(x1, x2)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
        print(f"{out.shape=}")
        print("Time: {:.3f} s".format((time.time() - time_stamp) / 10))

    flops, params = profile(model, inputs=(x1, x2), verbose=False)
    print(
        "FLOPs: {:.3f}T, Params: {:.2f}M".format(
            flops / 1000 / 1000 / 1000 / 1000, params / 1000 / 1000
        )
    )
