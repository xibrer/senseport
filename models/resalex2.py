import torch
import torch.nn as nn
# from models.MobileNet.MobileNetV1 import DepthSeparableConv1d, DepthSeparableConvTranspose1d
import torch.nn.functional as F


class BasicBlock(nn.Module):
    """Basic Block for resnet 18 and resnet 34

    """

    # BasicBlock and BottleNeck block
    # have different output size
    # we use class attribute expansion
    # to distinct
    expansion = 1

    def __init__(self, in_channels, out_channels, stride=2):
        super().__init__()

        # residual function
        self.residual_function = nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv1d(out_channels, out_channels * BasicBlock.expansion, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm1d(out_channels * BasicBlock.expansion)
        )

        # shortcut
        self.shortcut = nn.Sequential()

        # the shortcut output dimension is not the same with residual function
        # use 1*1 convolution to match the dimension
        if stride != 1 or in_channels != BasicBlock.expansion * out_channels:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_channels, out_channels * BasicBlock.expansion, kernel_size=1, stride=stride, bias=False),
                nn.BatchNorm1d(out_channels * BasicBlock.expansion)
            )

    def forward(self, x):
        return nn.ReLU(inplace=True)(self.residual_function(x) + self.shortcut(x))



class resalex(nn.Module):
    def __init__(self, num_classes=1):
        super().__init__()

        self.in_channels = 64
        self.conv1 = nn.Sequential(
            nn.Conv1d(1, 64, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm1d(64),
            nn.ReLU(inplace=True))
        self.conv2_x = self._make_layer(BasicBlock, 64, 1, 2)
        self.conv3_x = self._make_layer(BasicBlock, 128, 1, 2)
        self.conv4_x = self._make_layer(BasicBlock, 256, 1, 2)
        # self.conv5_x = self._make_layer(BasicBlock, 512, 1, 2)
        self.final_layer = nn.Sequential(nn.Conv1d(256,1,1),
                            nn.Linear(440,110),
                            nn.Dropout(0.2),
                            nn.Linear(110,num_classes),
                           )
    def _make_layer(self, block, out_channels, num_blocks, stride):
        """make resnet layers(by layer i didnt mean this 'layer' was the
        same as a neuron netowork layer, ex. conv layer), one layer may
        contain more than one residual block

        Args:
            block: block type, basic block or bottle neck block
            out_channels: output depth channel number of this layer
            num_blocks: how many blocks per layer
            stride: the stride of the first block of this layer

        Return:
            return a resnet layer
        """

        # we have num_block blocks per layer, the first block
        # could be 1 or 2, other blocks would always be 1
        strides = [stride] + [1] * (num_blocks - 1)
        layers = []
        for stride in strides:
            layers.append(block(self.in_channels, out_channels, stride))
            self.in_channels = out_channels * block.expansion

        return nn.Sequential(*layers)

    def forward(self, x):
        """The forward function takes in an image and returns the reconstructed image."""

        b_size = x.shape[0]
        output = self.conv1(x)
        output = self.conv2_x(output)
        # print(output.size())
        output = self.conv3_x(output)
        output = self.conv4_x(output)
        # output = self.conv5_x(output)
        # print(output.size())
        x_hat = self.final_layer(output)
        # x_hat = x_hat.reshape(b_size, 1, -1)
        return x_hat
