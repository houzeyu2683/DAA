import torch
from torch.utils.data import Dataset, DataLoader
from torch.utils.data import random_split
import os

class MyCustomDataset(Dataset):
    def __init__(self, data_dir, transform=None):
        """
        Args:
            data_dir (string): 資料夾路徑，存放你的資料。
            transform (callable, optional): 對資料進行轉換的操作（例如 torchvision.transforms）。
        """
        self.data_dir = data_dir
        self.transform = transform
        
        # 這裡先建立一個範例的檔案清單，實際使用時請根據你的資料格式修改
        # 例如：self.file_names = [f for f in os.listdir(data_dir) if f.endswith('.npy')]
        self.file_names = [] # TODO: 填入你的檔案清單
        
        # 範例用的 dummy data (實際請從檔案讀取)
        self.samples = [] 
        self.labels = []

    def __len__(self):
        """回傳 dataset 的總數量"""
        return len(self.file_names)

    def __getitem__(self, idx):
        """
        根據索引 idx 回傳一個樣本。
        """
        # 1. 取得檔案路徑或索引
        # file_path = os.path.join(self.data_dir, self.file_names[idx])
        
        # 2. 讀取資料 (範例使用隨機產生，請改為實際讀取邏輯)
        # data = torch.load(file_path) 
        data = torch.randn(3, 224, 224) # 範例：隨機產生一個影像形狀
        label = torch.tensor(0)          # 範例：隨機標籤
        
        # 3. 套用轉換 (Transform)
        if self.transform:
            data = self.transform(data)
            
        return data, label

def get_dataloader(data_dir, batch_size=32, train_ratio=0.8, transform=None):
    """
    建立 DataLoader 的輔助函式，包含自動切分訓練集與驗證集。
    """
    full_dataset = MyCustomDataset(data_dir, transform=transform)
    
    # 計算切分數量
    train_size = int(train_ratio * len(full_dataset))
    val_size = len(full_dataset) - train_size
    
    # 隨機切分
    train_dataset, val_dataset = random_split(full_dataset, [train_size, val_size])
    
    # 建立 DataLoader
    train_loader = DataLoader(
        train_dataset, 
        batch_size=batch_size, 
        shuffle=True, 
        num_workers=2  # 根據你的 CPU 核心數調整
    )
    
    val_loader = DataLoader(
        val_dataset, 
        batch_size=batch_size, 
        shuffle=False, 
        num_workers=2
    )
    
    return train_loader, val_loader

if __name__ == "__main__":
    # 測試用程式碼
    DATA_PATH = "path/to/your/data"
    
    # 建立 loader
    # train_loader, val_loader = get_dataloader(DATA_PATH, batch_size=16)
    
    # print(f"Dataset size: {len(MyCustomDataset(DATA_PATH))}")
    print("Template ready. Please modify MyCustomDataset class to load your actual data.")
