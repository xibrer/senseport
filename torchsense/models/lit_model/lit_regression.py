import lightning as L
import torch
from torchmetrics.functional.classification.accuracy import accuracy
import torch.optim as optim
import torch.nn.functional as F
import torch.nn as nn
from torchmetrics.regression import MeanSquaredError
import numpy as np


class LitRegressModel(L.LightningModule):
    def __init__(self, model, loss_fn=None, lr=0.0001, gamma=0.7) -> None:
        super().__init__()
        self.save_hyperparameters(ignore=['model'])
        self.model = model
        self.model.apply(self.weights_init)
        self.total_train_loss = []
        self.validation_step_outputs = []
        if loss_fn:
            self.loss_fn = MeanSquaredError()
        else:
            self.loss_fn = loss_fn

    def forward(self, x: torch.Tensor):
        return self.model(x)

    def _calculate_loss(self, batch, mode="train"):
        x = batch[0]
        y = batch[1]
        if not isinstance(x, torch.Tensor):
            x = tuple(x)
        preds = self.model(x)

        loss = self.loss_fn(preds.squeeze(1), y.squeeze(1))
        if mode == "train":
            self.total_train_loss.append(loss)
        else:
            self.validation_step_outputs.append(loss)
        self.log("%s_loss" % mode, loss, prog_bar=True, on_step=mode == "train", on_epoch=mode == "val")

        return loss

    def configure_optimizers(self):
        optimizer = optim.AdamW(self.parameters(), lr=self.hparams.lr)
        scheduler = optim.lr_scheduler.MultiStepLR(optimizer, milestones=[5, 10], gamma=0.1)
        # optimizer = optim.Adadelta(self.parameters(), lr=self.hparams.lr)
        # lr_scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=1, gamma=self.hparams.gamma)
        return [optimizer], [scheduler]

    def training_step(self, batch, batch_idx):
        loss = self._calculate_loss(batch, mode="train")
        return loss

    def on_train_epoch_end(self):
        # log epoch metric
        stacked_tensors = torch.stack(self.total_train_loss)
        # 计算堆叠张量的均值
        mean_tensor = torch.mean(stacked_tensors, dim=0)
        self.log('train_loss_epoch', mean_tensor)
        self.total_train_loss = []

    def validation_step(self, batch, batch_idx):
        self._calculate_loss(batch, mode="val")

    def on_validation_epoch_end(self):
        stacked_tensors = torch.stack(self.validation_step_outputs)
        # 计算堆叠张量的均值
        mean_tensor = torch.mean(stacked_tensors, dim=0)
        self.log('val_loss_epoch', mean_tensor)
        self.validation_step_outputs.clear()

    def test_step(self, batch, batch_idx):
        self._calculate_loss(batch, mode="test")

    def weights_init(self, m):
        if isinstance(m, nn.Conv2d) or isinstance(m, nn.ConvTranspose2d):
            nn.init.normal_(m.weight.data, 0.0, 0.02)
            if m.bias is not None:
                nn.init.constant_(m.bias.data, 0)
        elif isinstance(m, nn.BatchNorm2d):
            nn.init.normal_(m.weight.data, 1.0, 0.02)
            nn.init.constant_(m.bias.data, 0)
        # 对于任何其他类型的模块，如果它有子模块，则递归地应用 weights_init 函数
        elif isinstance(m, nn.Module):
            for name, child in m.named_children():
                self.weights_init(child)
