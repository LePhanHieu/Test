import os
from pathlib import Path
import torch

# ==== ĐƯỜNG DẪN ====
PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE = Path(os.getenv('SKIN_CANCER_BASE', str(PROJECT_ROOT / 'skin_cancer')))
DATA_DIR = Path(os.getenv('ISIC_DATA_DIR', str(PROJECT_ROOT / 'data' / 'isic2019')))

# ==== HẰNG SỐ ====
CLASSES = ['MEL', 'NV', 'BCC', 'AK', 'BKL', 'DF', 'VASC', 'SCC']
MALIGNANT = ['MEL', 'BCC', 'SCC', 'AK']
NUM_CLASSES = 8
IMG_SIZE = 224
BATCH_SIZE = 32

DEVICE = 'cuda' if torch.cuda.is_available() else 'cpu'

# Tạo folder nếu chưa có
for sub in ['checkpoints', 'results', 'figures', 'test_examples']:
    os.makedirs(os.path.join(BASE, sub), exist_ok=True)
