"""
SETU Project — Phase 3
Model: SegFormer-B2 with Cross-Attention Fusion
Phase 3 = optical only | Phase 5 = optical + SAR
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import SegformerModel, SegformerConfig


class CrossAttentionBlock(nn.Module):
    """
    Window-based cross-attention between optical and SAR feature maps.

    Partitions both feature maps into windows of size (win_h x win_w),
    runs multi-head cross-attention within each window independently,
    then reassembles. Memory is O(win_h * win_w) not O(H * W).

    Default window 8x8 = 64 tokens per window.
    At 512x512 input after SegFormer stage 4: feature map ~32x32.
    Windows: (32/8)^2 = 16 windows, each 64 tokens. Trivial memory.
    """

    def __init__(self, dim, num_heads=4, win_size=8, dropout=0.1):
        super().__init__()
        assert dim % num_heads == 0, f"dim {dim} must be divisible by num_heads {num_heads}"
        self.num_heads = num_heads
        self.win_size  = win_size
        self.head_dim  = dim // num_heads
        self.scale     = self.head_dim ** -0.5

        self.q_proj = nn.Linear(dim, dim)
        self.k_proj = nn.Linear(dim, dim)
        self.v_proj = nn.Linear(dim, dim)
        self.out    = nn.Linear(dim, dim)
        self.norm1  = nn.LayerNorm(dim)
        self.norm2  = nn.LayerNorm(dim)
        self.drop   = nn.Dropout(dropout)

    def _partition_windows(self, x, win_size):
        """
        x: (B, H, W, C)
        Returns: (num_windows*B, win_h*win_w, C)
        """
        B, H, W, C = x.shape
        x = x.view(B, H // win_size, win_size, W // win_size, win_size, C)
        x = x.permute(0, 1, 3, 2, 4, 5).contiguous()
        return x.view(-1, win_size * win_size, C)

    def _merge_windows(self, x, win_size, H, W):
        """
        x: (num_windows*B, win_h*win_w, C)
        Returns: (B, H, W, C)
        """
        B_times_nW, _, C = x.shape
        nH = H // win_size
        nW = W // win_size
        B  = B_times_nW // (nH * nW)
        x  = x.view(B, nH, nW, win_size, win_size, C)
        x  = x.permute(0, 1, 3, 2, 4, 5).contiguous()
        return x.view(B, H, W, C)

    def _pad_to_window(self, x, win_size):
        """Pad H and W to be divisible by win_size."""
        _, H, W, _ = x.shape
        pad_h = (win_size - H % win_size) % win_size
        pad_w = (win_size - W % win_size) % win_size
        if pad_h > 0 or pad_w > 0:
            x = F.pad(x, (0, 0, 0, pad_w, 0, pad_h))
        return x, H, W

    def forward(self, opt_feat, sar_feat):
        """
        opt_feat: (B, C, H, W) — optical feature map (query source)
        sar_feat: (B, C, H, W) — SAR feature map (key/value source)
        Returns:  (B, C, H, W) — attended optical features
        """
        B, C, H, W = opt_feat.shape

        # (B, C, H, W) -> (B, H, W, C) for window partitioning
        opt = opt_feat.permute(0, 2, 3, 1)
        sar = sar_feat.permute(0, 2, 3, 1)

        # Pad to window size
        opt, H_orig, W_orig = self._pad_to_window(opt, self.win_size)
        sar, _,      _      = self._pad_to_window(sar, self.win_size)
        _, Hp, Wp, _ = opt.shape

        # Residual before attention
        residual = opt

        # LayerNorm
        opt = self.norm1(opt)
        sar = self.norm2(sar)

        # Partition into windows: (nW*B, win^2, C)
        opt_w = self._partition_windows(opt, self.win_size)
        sar_w = self._partition_windows(sar, self.win_size)

        # Multi-head projections
        nWB = opt_w.shape[0]
        Q = self.q_proj(opt_w).view(nWB, -1, self.num_heads, self.head_dim).transpose(1, 2)
        K = self.k_proj(sar_w).view(nWB, -1, self.num_heads, self.head_dim).transpose(1, 2)
        V = self.v_proj(sar_w).view(nWB, -1, self.num_heads, self.head_dim).transpose(1, 2)

        # Attention within each window: (nWB, heads, win^2, win^2)
        attn = F.softmax(torch.matmul(Q, K.transpose(-2, -1)) * self.scale, dim=-1)
        attn = self.drop(attn)

        # Weighted values
        out = torch.matmul(attn, V)                           # (nWB, heads, win^2, head_dim)
        out = out.transpose(1, 2).contiguous()                 # (nWB, win^2, heads, head_dim)
        out = out.view(nWB, self.win_size * self.win_size, C)  # (nWB, win^2, C)
        out = self.out(out)

        # Merge windows back
        out = self._merge_windows(out, self.win_size, Hp, Wp)  # (B, Hp, Wp, C)

        # Remove padding
        out = out[:, :H_orig, :W_orig, :].contiguous()
        residual = residual[:, :H_orig, :W_orig, :].contiguous()

        # Residual connection
        out = residual + out

        # Back to (B, C, H, W)
        return out.permute(0, 3, 1, 2).contiguous()


class SEGFormerRoadExtractor(nn.Module):
    def __init__(self, num_classes=1, use_sar=False):
        super().__init__()
        self.use_sar     = use_sar
        self.hidden_sizes = [64, 128, 320, 512]
        self.decoder_dim  = 256

        # Optical encoder — pretrained ImageNet
        # Optical encoder — pretrained ImageNet
        self.optical_encoder = SegformerModel.from_pretrained(
            "nvidia/mit-b2",
            output_hidden_states=True,
            ignore_mismatched_sizes=True,
            use_safetensors=True
        )

        if use_sar:
            config = SegformerConfig.from_pretrained("nvidia/mit-b2")
            config.num_channels = 2
            self.sar_encoder = SegformerModel(config)
            self.cross_attention_blocks = nn.ModuleList([
                CrossAttentionBlock(dim=self.decoder_dim) for _ in range(4)
            ])
            self.sar_projections = nn.ModuleList([
                nn.Sequential(
                    nn.Conv2d(s, self.decoder_dim, 1),
                    nn.BatchNorm2d(self.decoder_dim),
                    nn.ReLU(inplace=True)
                ) for s in self.hidden_sizes
            ])
            print("Model: Dual-encoder (optical + SAR)")
        else:
            print("Model: Optical-only (Phase 3)")

        self.optical_projections = nn.ModuleList([
            nn.Sequential(
                nn.Conv2d(s, self.decoder_dim, 1),
                nn.BatchNorm2d(self.decoder_dim),
                nn.ReLU(inplace=True)
            ) for s in self.hidden_sizes
        ])

        self.fusion = nn.Sequential(
            nn.Conv2d(self.decoder_dim * 4, self.decoder_dim, 1),
            nn.BatchNorm2d(self.decoder_dim),
            nn.ReLU(inplace=True),
            nn.Dropout2d(0.1),
            nn.Conv2d(self.decoder_dim, self.decoder_dim // 2, 3, padding=1),
            nn.BatchNorm2d(self.decoder_dim // 2),
            nn.ReLU(inplace=True)
        )

        self.head = nn.Conv2d(self.decoder_dim // 2, num_classes, 1)

    def _decode(self, opt_hidden, target_size, sar_hidden=None):
        B    = opt_hidden[0].shape[0]
        H, W = target_size
        decoded = []

        for i in range(4):
            opt_proj = self.optical_projections[i](opt_hidden[i])

            if self.use_sar and sar_hidden is not None:
                sar_proj = self.sar_projections[i](sar_hidden[i])
                opt_proj = self.cross_attention_blocks[i](opt_proj, sar_proj)

            upsampled = F.interpolate(opt_proj, size=(H // 4, W // 4),
                                      mode='bilinear', align_corners=False)
            decoded.append(upsampled)

        fused  = self.fusion(torch.cat(decoded, dim=1))
        logits = self.head(fused)
        return F.interpolate(logits, size=(H, W), mode='bilinear', align_corners=False)

    def forward(self, optical_image, sar_image=None):
        B, C, H, W = optical_image.shape

        opt_out    = self.optical_encoder(pixel_values=optical_image,
                                          output_hidden_states=True)
        opt_hidden = opt_out.hidden_states

        sar_hidden = None
        if self.use_sar and sar_image is not None:
            sar_out    = self.sar_encoder(pixel_values=sar_image,
                                          output_hidden_states=True)
            sar_hidden = sar_out.hidden_states

        return self._decode(opt_hidden, (H, W), sar_hidden)


class DiceLoss(nn.Module):
    def __init__(self, smooth=1.0):
        super().__init__()
        self.smooth = smooth

    def forward(self, pred, target):
        pred   = torch.sigmoid(pred)
        p_flat = pred.view(-1)
        t_flat = target.view(-1)
        inter  = (p_flat * t_flat).sum()
        return 1 - (2. * inter + self.smooth) / (p_flat.sum() + t_flat.sum() + self.smooth)


class CombinedLoss(nn.Module):
    def __init__(self, dice_w=0.5, bce_w=0.5):
        super().__init__()
        self.dice   = DiceLoss()
        self.bce    = nn.BCEWithLogitsLoss()
        self.dice_w = dice_w
        self.bce_w  = bce_w

    def forward(self, pred, target):
        return self.dice_w * self.dice(pred, target) + self.bce_w * self.bce(pred, target)


if __name__ == "__main__":
    print("Testing model...")
    model = SEGFormerRoadExtractor(num_classes=1, use_sar=False)
    x     = torch.randn(2, 3, 512, 512)
    with torch.no_grad():
        out = model(x)
    print(f"Input:  {x.shape}")
    print(f"Output: {out.shape}  (expected: (2, 1, 512, 512))")
    total = sum(p.numel() for p in model.parameters())
    print(f"Params: {total:,}")
    print("Model OK — proceed to train.py")