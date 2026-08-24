"""
SETU Project — Phase 3
PyTorch Dataset: Mumbai + Khartoum
Fixed: image resize to 512x512 + CoarseDropout syntax
"""

import os
import random
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
import rasterio
import albumentations as A
from albumentations.pytorch import ToTensorV2
from pathlib import Path


class RoadDataset(Dataset):
    def __init__(self, prepared_dir, cities, split='train',
                 val_ratio=0.15, test_ratio=0.15, seed=42,
                 img_size=512):
        self.split    = split
        self.img_size = img_size
        self.samples  = []
        all_samples   = []

        for city in cities:
            img_dir  = Path(prepared_dir) / city / "images"
            mask_dir = Path(prepared_dir) / city / "masks"

            if not img_dir.exists():
                print(f"WARNING: {city} not found, skipping")
                continue

            images = sorted(list(img_dir.glob("*.tif")))
            found  = 0
            for img_path in images:
                mask_path = mask_dir / (img_path.stem + "_mask.tif")
                if mask_path.exists():
                    all_samples.append((str(img_path), str(mask_path)))
                    found += 1

            print(f"  {city}: {found} valid pairs")

        random.seed(seed)
        random.shuffle(all_samples)

        n       = len(all_samples)
        n_test  = int(n * test_ratio)
        n_val   = int(n * val_ratio)
        n_train = n - n_test - n_val

        if split == 'train':
            self.samples = all_samples[:n_train]
        elif split == 'val':
            self.samples = all_samples[n_train:n_train + n_val]
        else:
            self.samples = all_samples[n_train + n_val:]

        print(f"  Split '{split}': {len(self.samples)} samples")

        # -------------------------------------------------------
        # AUGMENTATIONS
        # Resize to img_size FIRST — critical fix for 1300px images
        # -------------------------------------------------------
        # -------------------------------------------------------
        # AUGMENTATIONS
        # Resize to img_size FIRST — critical fix for 1300px images
        # -------------------------------------------------------
        if split == 'train':
            self.transform = A.Compose([
                A.Resize(img_size, img_size),
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.5),
                A.RandomRotate90(p=0.5),
                A.RandomBrightnessContrast(
                    brightness_limit=0.2,
                    contrast_limit=0.2,
                    p=0.5
                ),
                A.GaussNoise(p=0.3),
                # FIX: Explicitly apply to image only. Do not corrupt the mask.
                #A.CoarseDropout(
                 #   num_holes_range=(1, 8),
                  #  hole_height_range=(16, 32),
                   # hole_width_range=(16, 32),
                    #fill_value=0, # Use fill_value instead of fill
                    #mask_fill_value=None, # Crucial: do not alter the mask
                    #p=0.3
                #),
                A.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
                ToTensorV2()
            ])
        else:
            # FIX: Restored the validation/test transforms
            self.transform = A.Compose([
                A.Resize(img_size, img_size),
                A.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                ),
                ToTensorV2()
            ])

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        img_path, mask_path = self.samples[idx]

        # Load image RGB
        # Load image RGB
        with rasterio.open(img_path) as src:
            img = src.read([1, 2, 3])
            img = np.transpose(img, (1, 2, 0)).astype(np.float32)
            
            # FIX: Per-channel percentile normalization
            p2  = np.percentile(img, 2, axis=(0, 1))
            p98 = np.percentile(img, 98, axis=(0, 1))
            
            # Clip and normalize each channel independently
            img = np.clip(img, p2, p98)
            img = (img - p2) / (p98 - p2 + 1e-6) * 255.0
            img = img.astype(np.uint8)

        # Load mask
        with rasterio.open(mask_path) as src:
            mask = src.read(1).astype(np.float32)
            mask = (mask > 0).astype(np.float32)

        augmented = self.transform(image=img, mask=mask)
        image = augmented['image']
        mask  = augmented['mask'].unsqueeze(0)

        return image, mask


def get_dataloaders(prepared_dir, cities, batch_size=4,
                    num_workers=0, img_size=512):
    print("\nBuilding datasets...")
    pin = torch.cuda.is_available()  # only pin if GPU available

    train_ds = RoadDataset(prepared_dir, cities, split='train',  img_size=img_size)
    val_ds   = RoadDataset(prepared_dir, cities, split='val',    img_size=img_size)
    test_ds  = RoadDataset(prepared_dir, cities, split='test',   img_size=img_size)

    train_loader = DataLoader(train_ds, batch_size=batch_size,
                              shuffle=True,  num_workers=num_workers, pin_memory=pin)
    val_loader   = DataLoader(val_ds,   batch_size=batch_size,
                              shuffle=False, num_workers=num_workers, pin_memory=pin)
    test_loader  = DataLoader(test_ds,  batch_size=batch_size,
                              shuffle=False, num_workers=num_workers, pin_memory=pin)

    print(f"DataLoaders ready — batch: {batch_size}, img_size: {img_size}x{img_size}")
    return train_loader, val_loader, test_loader


if __name__ == "__main__":
    PREPARED_DIR = r"C:\Users\omkar\OneDrive\Desktop\sih\spacenet_prepared"
    CITIES       = ["Mumbai", "Khartoum"]

    train_loader, val_loader, test_loader = get_dataloaders(
        PREPARED_DIR, CITIES, batch_size=4, img_size=512
    )

    images, masks = next(iter(train_loader))
    print(f"\nBatch check:")
    print(f"  Images shape:     {images.shape}   (expected: [4, 3, 512, 512])")
    print(f"  Masks shape:      {masks.shape}    (expected: [4, 1, 512, 512])")
    print(f"  Image min/max:    {images.min():.3f} / {images.max():.3f}")
    print(f"  Mask unique vals: {masks.unique()}")

    if list(images.shape) == [4, 3, 512, 512]:
        print("\n  Shape OK — proceed to train.py")
    else:
        print("\n  WARNING: Shape not 512x512 — check img_size parameter")