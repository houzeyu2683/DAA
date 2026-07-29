# App Project

This directory contains the core application logic, including data loading utilities.

## Directory Structure

```text
app/
├── data_loader.py    # Custom PyTorch Dataset and DataLoader templates
├── hello.py          # Entry point or simple test script
└── README.md         # Project documentation
```

## Files

### `data_loader.py`
This module provides a template for handling custom datasets using PyTorch. It includes:
- `MyCustomDataset`: A base class for implementing custom data loading logic.
- `get_dataloader`: A utility function to automatically split data into training and validation sets and return corresponding `DataLoader` objects.

**How to use:**
1. Inherit from `MyCustomDataset`.
2. Implement the `__init__`, `__len__`, and `__getitem__` methods to suit your specific data format (e.g., images, CSV, NumPy arrays).
3. Use `get_dataloader` to prepare your training and validation loops.

### `hello.py`
A simple script for testing the environment or basic application flow.

## Getting Started

1. **Environment Setup**:
   Ensure you have `torch` installed:
   ```bash
   pip install torch
   ```

2. **Running Tests**:
   You can run the data loader template to check for syntax errors:
   ```bash
   python app/data_loader.py
   ```
